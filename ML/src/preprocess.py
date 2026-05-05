"""
This module process the raw csv to cleaned csv, run this if you don't have the cleaned file yet.
"""

import pandas as pd

from config import (
    MAX_CLEAN_ROWS,
    PROCESSED_311_PATH,
    RAW_311_PATH,
    SOURCE_COLUMNS,
    RENAMED_COLUMNS,
    OUTPUT_COLUMNS,
)

df = pd.read_csv(
    RAW_311_PATH,
    usecols=SOURCE_COLUMNS,
    nrows=MAX_CLEAN_ROWS,
    low_memory=False,
)

df = df.rename(columns=RENAMED_COLUMNS)
df["Created Date"] = df["Created Date"].astype("string").str.strip()
df["Problem"] = df["Problem"].astype("string").str.strip()
df["Problem Detail"] = df["Problem Detail"].astype("string").str.strip()
df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")

df = df[OUTPUT_COLUMNS].dropna()
df.to_csv(PROCESSED_311_PATH, index=False)

print(f"Cleaned dataset written to {PROCESSED_311_PATH}")
