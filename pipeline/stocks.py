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