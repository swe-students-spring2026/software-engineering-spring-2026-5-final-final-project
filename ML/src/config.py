"""
This module provides configs for the project.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

RAW_311_FILENAME = "311_Service_Requests_from_2020_to_Present_20260321.csv" # the 13GB raw dataset, should not be in deployment pipeline
PROCESSED_311_FILENAME = "cleaned_311.csv"
EMBEDDED_311_FILENAME = "cleaned_311.npy"
EMBEDDINGS_MODEL = "sentence-transformers/all-MiniLM-L6-v2" # can use even smaller model if necessary

RAW_311_PATH = RAW_DIR / RAW_311_FILENAME
PROCESSED_311_PATH = PROCESSED_DIR / PROCESSED_311_FILENAME
EMBEDDINGS_311_PATH = PROCESSED_DIR / EMBEDDED_311_FILENAME

MAX_CLEAN_ROWS = 1000000 # 80MB of size, can be lower if necessary
TOTAL_K = 30
CATEGORY_TOP_K = 20 # can be higher if necessary
CLUSTER_TOPK = 5

SOURCE_COLUMNS = [
    "Created Date",
    "Problem (formerly Complaint Type)",
    "Problem Detail (formerly Descriptor)",
    "Longitude",
    "Latitude",
]

RENAMED_COLUMNS = {
    "Problem (formerly Complaint Type)": "Problem",
    "Problem Detail (formerly Descriptor)": "Problem Detail",
}

OUTPUT_COLUMNS = [
    "Created Date",
    "Problem",
    "Problem Detail",
    "Longitude",
    "Latitude",
]

RAW_FACILITIES_FILENAME = "Facilities_Database_20260429.csv"
PROCESSED_FACILITIES_FILENAME = "cleaned_facilities.csv"

RAW_FACILITIES_PATH = RAW_DIR / RAW_FACILITIES_FILENAME
PROCESSED_FACILITIES_PATH = PROCESSED_DIR / PROCESSED_FACILITIES_FILENAME


EMBEDDED_FACILITIES_FILENAME = "cleaned_facilities.npy"
EMBEDDINGS_FACILITIES_PATH = PROCESSED_DIR / EMBEDDED_FACILITIES_FILENAME

FACILITIES_SOURCE_COLUMNS = [
    "facname",
    "boro",
    "latitude",
    "longitude",
    "facgroup",
    "facsubgrp",
    "factype",
]

FACILITIES_OUTPUT_COLUMNS = [
    "facname",
    "facgroup",
    "facsubgrp",
    "factype",
    "boro",
    "longitude",
    "latitude",
]
