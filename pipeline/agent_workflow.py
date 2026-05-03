import argparse
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import pandas as pd
import requests
from dotenv import load_dotenv
from matplotlib.backends.backend_pdf import PdfPages

from mongo_store import get_mongo_store

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
SCREENING_FEATHER = BASE_DIR / "screening_output" / "final_screening_union.feather"
CHART_MANIFEST_CSV = BASE_DIR / "screening_output" / "chart_manifest.csv"
AGENTS_DATA_PACKAGE_DIR = BASE_DIR / "agents_data_package"
OUTPUT_ROOT = BASE_DIR / "output" / "agent_runs"

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

ANALYST_SYSTEM_PROMPT = """You are a stock analyst evaluating one ticker.

Decide if this is a REAL but INCOMPLETE repricing opportunity. The stock price has most likely increased a reasonable degree already, because this is a momentum strategy. 
Your goal is to figure out if the underlying fundamental catalyst is so large the the recent move still is not enough to price it in yet.  
Start from attached package files. 
Feel free to use web research, but also remember you already have some preliminary info uplaoded. 
If something is uncertain, use web search.
Be blunt, evidence-based, and decision-oriented. If financial models/valuation is necessary, do it.

Return exactly:
1) Executive Verdict (rating + stage + confidence)
2) What Changed
3) Why It Matters Economically
4) Evidence It Is Real (hard vs soft)
5) What Is Already Priced In
6) Remaining Uncertainty
7) Bull/Base/Bear (returns + probabilities summing to 100%)
8) Repricing vs Mean Reversion Probabilities
9) Disconfirming Signals (3-5)
10) Final Recommendation

End with:
FINAL_JSON:
{
  "ticker": "...",
  "rating": "Reject | Watchlist | Research Deeper | Buy Candidate",
  "repricing_stage": "Early | Middle | Late | Unclear",
  "confidence": "Low | Medium | High",
  "prob_upward_repricing": 0,
  "prob_mean_reversion": 0,
  "bull_case_return_pct": 0,
  "bull_case_prob": 0,
  "base_case_return_pct": 0,
  "base_case_prob": 0,
  "bear_case_return_pct": 0,
  "bear_case_prob": 0,
  "expected_return_pct": 0,
  "top_disconfirming_signals": ["", "", ""]
}
"""
def get_api_key() -> str:
    """Get API key from env; error if missing."""
    key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY")
    if not key:
        raise RuntimeError("Missing OPENAI_API_KEY (or OPENAI_KEY).")
    return key


def build_run_dirs(run_id: Optional[str]) -> Dict[str, Path]:
    """Create run folders and return their paths."""
    run_name = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    root = OUTPUT_ROOT / run_name
    per_stock, charts, uploaded = root/"per_stock", root/"charts", root/"uploaded_file_manifest"
    for d in (root, per_stock, charts, uploaded):
        d.mkdir(parents=True, exist_ok=True)
    return {"root": root, "per_stock": per_stock, "charts": charts, "uploaded": uploaded}