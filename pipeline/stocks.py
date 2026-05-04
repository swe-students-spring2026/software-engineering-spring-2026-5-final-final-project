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
# remove 516
