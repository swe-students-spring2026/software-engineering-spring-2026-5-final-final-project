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