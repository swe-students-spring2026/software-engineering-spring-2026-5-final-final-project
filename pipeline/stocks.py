"""Stock trend-scoring helpers used by the pipeline."""

# remove -  395
def safe_ratio(
    recent: float, old: float, clip_min: float = 0.05, clip_max: float = 10.0
) -> float:
    """Safe division - clamps the ratio so one bad data point doesn't wreck the score."""
    if pd.isna(recent) or pd.isna(old):
        return np.nan
    recent_adj = max(float(recent), clip_min)
    old_adj = max(float(old), clip_min)
    ratio = recent_adj / old_adj
    return min(max(ratio, 1 / clip_max), clip_max)


def trend_to_noise_ratio(price_series: pd.Series) -> float:
    """How much of the total wiggle is actualy directed movement (1.0 = perfect trend)."""
    s = pd.Series(price_series).dropna().copy()
    if len(s) < 3:
        return np.nan
    if s.iloc[0] <= 0 or s.iloc[-1] <= 0:
        return np.nan

    log_ret = np.log(s / s.shift(1)).dropna()
    if len(log_ret) == 0:
        return np.nan

    net_log_move = abs(np.log(s.iloc[-1] / s.iloc[0]))
    total_abs_log_move = np.abs(log_ret).sum()
    if total_abs_log_move == 0:
        return np.nan
    return float(net_log_move / total_abs_log_move)


def quadratic_log_fit_r2(price_series: pd.Series) -> Tuple[float, float]:
    """Fit a quadratic to log-prices; negative curvature means the trend is flatenning."""
    s = pd.Series(price_series).dropna().copy()
    if len(s) < 5:
        return np.nan, np.nan
    if (s <= 0).any():
        return np.nan, np.nan

    y = np.log(s.values)
    t = np.arange(len(y))
    c_quad, b_quad, a_quad = np.polyfit(t, y, 2)
    y_hat = a_quad + b_quad * t + c_quad * (t**2)
    ss_res = np.sum((y - y_hat) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2 = np.nan if ss_tot == 0 else 1 - ss_res / ss_tot
    return float(c_quad), float(r2)


def analyze_one_stock(series: pd.Series, cfg: PipelineConfig) -> Optional[dict]:
    """Main per-stock analysis - returns None if the stock doesn't pass our quality bar."""
    s = pd.to_numeric(pd.Series(series), errors="coerce").dropna().copy()
    if len(s) < cfg.min_trading_days:
        return None
    if s.iloc[0] <= 0 or s.iloc[-1] <= 0:
        return None

    start_price = float(s.iloc[0])
    end_price = float(s.iloc[-1])
    total_return_pct = (end_price / start_price - 1) * 100
    if total_return_pct < cfg.min_return_pct:
        return None
    if end_price < cfg.min_last_price:
        return None

    # score "is the trend getting cleaner and steeper lately?" by comparing
    # the older half of the chart to the recent half, not by fitting one model to the
    # whole period and hoping that tells the story.
    n = len(s)
    mid = n // 2
    old_s = s.iloc[:mid].copy()
    recent_s = s.iloc[mid:].copy()

    if len(old_s) < 20 or len(recent_s) < 20:
        return None
    if (old_s <= 0).any() or (recent_s <= 0).any():
        return None

    x_old = np.arange(len(old_s))
    y_old = np.log(old_s.to_numpy(dtype=float))
    reg_old = linregress(x_old, y_old)
    old_log_slope = float(reg_old.slope)
    old_r2 = float(reg_old.rvalue**2)
    old_tnr = trend_to_noise_ratio(old_s)

    x_recent = np.arange(len(recent_s))
    y_recent = np.log(recent_s.to_numpy(dtype=float))
    reg_recent = linregress(x_recent, y_recent)
    recent_log_slope = float(reg_recent.slope)
    recent_r2 = float(reg_recent.rvalue**2)
    recent_tnr = trend_to_noise_ratio(recent_s)

    if recent_r2 < cfg.min_recent_r2:
        return None
    if recent_log_slope <= 0:
        return None

    # ratios are clipped on purpose so one weird denominator does not blow up the ranking
    r2_ratio = safe_ratio(recent_r2, old_r2, cfg.ratio_clip_min, cfg.ratio_clip_max)
    slope_ratio = safe_ratio(
        recent_log_slope,
        max(old_log_slope, cfg.ratio_clip_min),
        cfg.ratio_clip_min,
        cfg.ratio_clip_max,
    )
    tnr_ratio = safe_ratio(recent_tnr, old_tnr, cfg.ratio_clip_min, cfg.ratio_clip_max)

    technical_score = (
        cfg.weight_r2_ratio * r2_ratio
        + cfg.weight_slope_ratio * slope_ratio
        + cfg.weight_tnr_ratio * tnr_ratio
    )

    quadratic_c_curvature, quadratic_r2 = quadratic_log_fit_r2(s)

    return {
        "n_days": len(s),
        "start_price": start_price,
        "end_price": end_price,
        "total_return_pct": total_return_pct,
        "technical_score": float(technical_score),
        "recent_r2_old_r2_ratio": r2_ratio,
        "recent_r2": recent_r2,
        "old_r2": old_r2,
        "recent_tnr_old_tnr_ratio": tnr_ratio,
        "recent_tnr": recent_tnr,
        "old_tnr": old_tnr,
        "recent_log_slope": recent_log_slope,
        "old_log_slope": old_log_slope,
        "recent_log_slope_old_log_slope_ratio": slope_ratio,
        "quadratic_c_curvature": quadratic_c_curvature,
        "quadratic_r2": quadratic_r2,
    }

def _clean_colname(col: str) -> str:
    # strip and fix unicode weirdness in column names
    return str(col).strip().replace("\xa0", " ").replace("\n", " ").replace("\r", " ")


def _to_float(x) -> float:
    # turns messy strings like "$1,234" or "(5)" into a float
    if pd.isna(x):
        return np.nan
    s = str(x).strip()
    if s in {"", "-", "nan", "None"}:
        return np.nan
    s = s.replace("$", "").replace(",", "").replace("%", "").replace("+", "")
    s = s.replace("(", "-").replace(")", "")
    try:
        return float(s)
    except Exception:
        return np.nan


def _extract_trade_code(val: str) -> Optional[str]:
    # grabs the code before the dash, e.g. "P - Purchase" -> "P"
    if pd.isna(val):
        return None
    s = str(val).strip()
    if not s:
        return None
    return s.split(" - ")[0].strip().upper()


def clean_numeric_series(s: pd.Series) -> pd.Series:
    # vectorised _to_float for a whole column
    return pd.to_numeric(
        s.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.replace("+", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.replace("(", "-", regex=False)
        .str.replace(")", "", regex=False)
        .str.strip(),
        errors="coerce",
    )


def parse_openinsider_table_from_html(html: str, ticker: str) -> pd.DataFrame:
    try:
        tables = pd.read_html(io.StringIO(html))
    except Exception:
        return pd.DataFrame()
    if len(tables) == 0:
        return pd.DataFrame()

    # the widest table is usualy the real trades one
    df = max(tables, key=lambda x: x.shape[1]).copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [" ".join([str(x) for x in col if str(x) != "nan"]).strip() for col in df.columns]
    else:
        df.columns = [str(c) for c in df.columns]
    df.columns = [re.sub(r"\s+", " ", str(c).replace("\xa0", " ")).strip() for c in df.columns]

    # map whatever column names we got to something consistant
    rename_map = {}
    for c in df.columns:
        cl = c.lower()
        if "filing" in cl and "date" in cl:
            rename_map[c] = "filing_date"
        elif "trade" in cl and "date" in cl:
            rename_map[c] = "trade_date"
        elif cl == "ticker":
            rename_map[c] = "Ticker"
        elif "insider name" in cl or cl == "insider":
            rename_map[c] = "insider_name"
        elif "trade type" in cl or "trade code" in cl:
            rename_map[c] = "trade_code"
        elif cl == "title":
            rename_map[c] = "title"
        elif cl in {"price", "qty", "owned", "value"}:
            rename_map[c] = cl
    df = df.rename(columns=rename_map)

    if "Ticker" not in df.columns:
        df["Ticker"] = ticker
    df["Ticker"] = df["Ticker"].astype(str).str.upper().str.strip()
    df = df[df["Ticker"] == ticker.upper()].copy()

    for c in ["filing_date", "trade_date"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    for c in ["value", "qty", "price", "owned"]:
        if c in df.columns:
            df[c] = clean_numeric_series(df[c])
    if "trade_code" in df.columns:
        df["trade_code"] = (
            df["trade_code"].astype(str).str.replace("\xa0", " ", regex=False).str.replace(r"\s+", " ", regex=True).str.upper().str.strip()
        )
    if "insider_name" in df.columns:
        df["insider_name"] = (
            df["insider_name"].astype(str).str.replace("\xa0", " ", regex=False).str.replace(r"\s+", " ", regex=True).str.strip()
        )
    return df


def fetch_openinsider_ticker_table(ticker: str, timeout: int = 20) -> pd.DataFrame:
    # fires the request; actual parsing is done seperately
    url = f"http://openinsider.com/search?q={ticker}"
    headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"}
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return parse_openinsider_table_from_html(resp.text, ticker=ticker)


def is_purchase_row(row: pd.Series) -> bool:
    # openinsider uses "P" prefix for outright purchases
    if "trade_code" not in row.index or pd.isna(row["trade_code"]):
        return False
    return str(row["trade_code"]).upper().strip().startswith("P")


def summarize_insider(df: pd.DataFrame, lookback_days: int, market_cap: float) -> dict:
    base = {
        "buy_dollars_60d": 0.0,
        "unique_buyers_60d": 0,
        "insider_score_60d": 0.0,
        "n_insider_rows": 0,
    }
    if df is None or df.empty:
        return base
    date_col = "trade_date" if "trade_date" in df.columns else "filing_date"
    if date_col not in df.columns:
        return base
    # only look at trades within the lookback window
    cutoff = pd.Timestamp.now().normalize() - pd.Timedelta(days=lookback_days)
    df = df[df[date_col] >= cutoff].copy()
    if df.empty:
        return base

    buys = df[df.apply(is_purchase_row, axis=1)].copy() if "trade_code" in df.columns else pd.DataFrame(columns=df.columns)
    if "value" in buys.columns:
        buys["value"] = pd.to_numeric(buys["value"], errors="coerce").fillna(0)
        buy_dollars = float(buys["value"].sum())
    else:
        buy_dollars = 0.0
    if "insider_name" in buys.columns:
        unique_buyers = int(buys["insider_name"].dropna().astype(str).str.strip().nunique())
    else:
        unique_buyers = 0
    # This is a homemade score, not a finance-standard metric. It rewards more dollars
    # and more distinct buyers, but uses log1p so one giant trade does not dominate everything.
    insider_score = math.log1p(max(buy_dollars, 0)) * (1 + 0.25 * unique_buyers)
    return {
        "buy_dollars_60d": buy_dollars,
        "unique_buyers_60d": unique_buyers,
        "insider_score_60d": float(insider_score),
        "n_insider_rows": int(len(df)),
    }
# remove 665

