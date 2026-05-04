import io
import json
import math
import os
import re
import shutil
import threading
import time
import warnings
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Optional, Tuple
import pandas as pd
import requests


warnings.filterwarnings("ignore")  # suppress noisy deprecation warnings
load_dotenv()  # pull in .env vars so we don't have to hardcode credentials


@dataclass
class PipelineConfig:
    # This is basically the script's control panel. Most of the "why did it do that?"
    # questions trace back to one of these thresholds or cache TTLs.
    universe_history_years: int = 3
    universe_min_market_cap: float = 100e6   # $100M floor to skip micro-caps
    universe_max_market_cap: float = 50e9   # $50B ceiling — true small/mid only
    screen_max_market_cap: float = 10e9
    lookback_months: int = 8               # how far back we look at price history
    min_return_pct: float = 30.0           # must be up at least 30% over lookback
    min_trading_days: int = 80
    min_last_price: float = 1.0            # filter out penny stocks
    min_recent_r2: float = 0.85            # trend must be fairly linear
    weight_r2_ratio: float = 0.50
    weight_slope_ratio: float = 0.30
    weight_tnr_ratio: float = 0.20
    ratio_clip_min: float = 0.05
    ratio_clip_max: float = 10.0
    meta_chunk_size: int = 150             # batch size for metadata fetches
    meta_sleep_sec: float = 0.05
    meta_max_workers: int = 4
    metadata_refresh_days: int = 7         # re-download metadata once a week
    download_chunk_size: int = 100
    price_sleep_sec: float = 0.02
    insider_lookback_days: int = 60        # look at last 2 months of insider filings
    insider_score_threshold: float = 25.0
    insider_max_workers: int = 8
    insider_timeout_sec: int = 12
    min_insider_coverage_ratio: float = 0.95
    package_max_workers: int = 6
    package_refresh_days: int = 60         # refresh agent data packages monthly
    sec_min_interval_sec: float = 0.12     # rate-limit SEC requests to stay polite
    sec_timeout_sec: int = 30
    sec_num_8k: int = 10                   # number of recent 8-K filings to pull

#folder paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
SCREENING_OUTPUT_DIR = BASE_DIR / "screening_output"
AGENTS_DATA_PACKAGE_DIR = BASE_DIR / "agents_data_package"
CHART_IMAGES_DIR = SCREENING_OUTPUT_DIR / "chart_images"
PRICE_FEATHER = DATA_DIR / "small_midcap_prices_3y.feather"
META_FEATHER = DATA_DIR / "small_midcap_meta.feather"
INSIDER_FEATHER = DATA_DIR / "insider_latest.feather"
INSIDER_SUMMARY_FEATHER = DATA_DIR / "insider_summary_latest.feather"

#splits a big list into chunks 
def chunk_list(items: List[str], n: int) -> Iterable[List[str]]:
    for i in range(0, len(items), n):
        yield items[i : i + n]

#scrapes the nasdaq website to the all the tickers on nasdaq and other exchanges
def download_nasdaq_symbol_dirs() -> Tuple[pd.DataFrame, pd.DataFrame]:
    nasdaq_url = "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt"
    other_url = "https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt"
    nasdaq_txt = requests.get(nasdaq_url, timeout=30).text
    other_txt = requests.get(other_url, timeout=30).text
    # both files are pipe-delimited; parse them into dataframes and return as a pair
    return pd.read_csv(io.StringIO(nasdaq_txt), sep="|"), pd.read_csv(io.StringIO(other_txt), sep="|")
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
