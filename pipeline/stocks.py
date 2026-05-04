import io
import math
import numpy as np
import pandas as pd
import warnings
import os

warnings.filterwarnings("ignore")
load_dotenv()


@dataclass
class PipelineConfig:
    # This is basically the script's control panel. Most of the "why did it do that?"
    # questions trace back to one of these thresholds or cache TTLs.
    universe_history_years: int = 3
    universe_min_market_cap: float = 100e6
    universe_max_market_cap: float = 50e9
    screen_max_market_cap: float = 10e9
    lookback_months: int = 8


#remove 1135
def _sec_headers() -> dict:
    # SEC blocks requests without a real email in User-Agent.
    user_agent = os.getenv("SEC_USER_AGENT", "StocksPipeline research your_email@example.com")
    return {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}


def _throttled_get(url: str, timeout: int, limiter: dict, headers: Optional[dict] = None) -> requests.Response:
    headers = headers or {}
    with limiter["lock"]:
        now = time.time()
        wait = limiter["next_ts"] - now
        if wait > 0:
            time.sleep(wait)
        limiter["next_ts"] = time.time() + limiter["interval"]  # update inside lock to prevent races
    resp = requests.get(url, timeout=timeout, headers=headers)
    resp.raise_for_status()
    return resp


def _select_recent_filings(df_recent: pd.DataFrame, cfg: PipelineConfig) -> pd.DataFrame:
    if df_recent.empty:
        return df_recent
    df = df_recent.copy()
    df["form_upper"] = df["form"].astype(str).str.upper()
    df["filingDate"] = pd.to_datetime(df["filingDate"], errors="coerce")
    # 1 annual, 2 quarterly, N event filings — most recent of each.
    k = df[df["form_upper"] == "10-K"].sort_values("filingDate", ascending=False).head(1)
    q = df[df["form_upper"] == "10-Q"].sort_values("filingDate", ascending=False).head(2)
    e = df[df["form_upper"] == "8-K"].sort_values("filingDate", ascending=False).head(cfg.sec_num_8k)
    out = pd.concat([k, q, e], ignore_index=True)
    return out.drop_duplicates(subset=["accessionNumber"])


def _build_sec_doc_url(cik_10: str, accession_number: str, primary_document: str) -> str:
    # SEC URLs need no dashes in the accession number and no leading zeros in the CIK.
    accession_nodashes = accession_number.replace("-", "")
    cik_no_leading_zeros = str(int(cik_10))
    return f"https://www.sec.gov/Archives/edgar/data/{cik_no_leading_zeros}/{accession_nodashes}/{primary_document}"


def build_agents_data_packages(
    final_df: pd.DataFrame, price_wide: pd.DataFrame, universe_meta: pd.DataFrame, cfg: PipelineConfig
) -> pd.DataFrame:
    AGENTS_DATA_PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    ticker_map_url = "https://www.sec.gov/files/company_tickers.json"
    sec_headers = _sec_headers()
    limiter = {"lock": threading.Lock(), "next_ts": 0.0, "interval": cfg.sec_min_interval_sec}

    try:
        ticker_map_resp = _throttled_get(ticker_map_url, cfg.sec_timeout_sec, limiter, headers=sec_headers).json()
        sec_ticker_to_cik = {str(v["ticker"]).upper(): str(v["cik_str"]).zfill(10) for v in ticker_map_resp.values()}
    except Exception:
        sec_ticker_to_cik = {}  # SEC unreachable; filings will be skipped

    # Remove stale ticker dirs no longer in the current universe.
    expected_tickers = {str(t).upper() for t in final_df["Ticker"].dropna().astype(str)}
    for child in AGENTS_DATA_PACKAGE_DIR.iterdir():
        if child.is_dir() and child.name.upper() not in expected_tickers:
            shutil.rmtree(child, ignore_errors=True)

    meta_map = (  # keyed by ticker for O(1) lookup below
        universe_meta[["Ticker", "Company", "sector", "industry", "market_cap_num"]]
        .drop_duplicates(subset=["Ticker"])
        .set_index("Ticker")
        .to_dict(orient="index")
    )

    wanted_fields = [
        "shortName",
        "longName",
        "sector",
        "industry",
        "marketCap",
        "enterpriseValue",
        "sharesOutstanding",
        "floatShares",
        "currentPrice",
        "previousClose",
        "fiftyTwoWeekHigh",
        "fiftyTwoWeekLow",
        "averageVolume",
        "averageVolume10days",
        "beta",
        "trailingPE",
        "priceToBook",
        "totalCash",
        "totalDebt",
        "revenueGrowth",
        "grossMargins",
        "operatingMargins",
        "ebitdaMargins",
    ]

    def _save_df(df_obj: pd.DataFrame, csv_path: Path) -> None:
        if df_obj is None or df_obj.empty:
            return
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        df_obj.to_csv(csv_path, index=True)

    def _to_ts(val) -> Optional[pd.Timestamp]:
        if val is None:
            return None
        ts = pd.to_datetime(val, errors="coerce")
        if pd.isna(ts):
            return None
        return pd.Timestamp(ts).normalize()

    today = pd.Timestamp.now().normalize()
#remove 1238
