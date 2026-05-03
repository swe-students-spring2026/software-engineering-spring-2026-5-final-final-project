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
    RAW_FACILITIES_PATH,
    PROCESSED_FACILITIES_PATH,
    FACILITIES_SOURCE_COLUMNS,
    FACILITIES_OUTPUT_COLUMNS,
)


def preprocess_311():
    """Preprocess the RAW 13GB data"""
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
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")

    df = df[OUTPUT_COLUMNS].dropna()
    df.to_csv(PROCESSED_311_PATH, index=False)

    print(f"Cleaned dataset written to {PROCESSED_311_PATH}")


def preprocess_facilities():
    """Preprocess the nyc facility dataset"""
    df = pd.read_csv(
        RAW_FACILITIES_PATH,
        usecols=FACILITIES_SOURCE_COLUMNS,
        low_memory=False,
    )

    df["facname"] = df["facname"].astype("string").str.strip()
    df["facgroup"] = df["facgroup"].astype("string").str.strip()
    df["facsubgrp"] = df["facsubgrp"].astype("string").str.strip()
    df["factype"] = df["factype"].astype("string").str.strip()
    df["boro"] = df["boro"].astype("string").str.strip()
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    df = df[FACILITIES_OUTPUT_COLUMNS].dropna()
    df = df[(df["longitude"] != 0.0) & (df["latitude"] != 0.0)]
    df.to_csv(PROCESSED_FACILITIES_PATH, index=False)

    print(f"Cleaned dataset written to {PROCESSED_FACILITIES_PATH}")


if __name__ == "__main__":
    preprocess_311()
    preprocess_facilities()
