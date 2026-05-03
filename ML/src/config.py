"""
This module provides configs for the project.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

RAW_311_FILENAME = "311_Service_Requests_from_2020_to_Present_20260321.csv"  # the 13GB raw dataset, should not be in deployment pipeline
PROCESSED_311_FILENAME = "cleaned_311.csv"
EMBEDDED_311_FILENAME = "cleaned_311.npy"
EMBEDDINGS_MODEL = (
    "sentence-transformers/all-MiniLM-L6-v2"  # can use even smaller model if necessary
)

LLM_MODEL = "Qwen/Qwen3.5-0.8B"
MAX_NEW_TOKENS = 128

RAW_311_PATH = RAW_DIR / RAW_311_FILENAME
PROCESSED_311_PATH = PROCESSED_DIR / PROCESSED_311_FILENAME
EMBEDDINGS_311_PATH = PROCESSED_DIR / EMBEDDED_311_FILENAME

MAX_CLEAN_ROWS = 1000000  # 80MB of size, can be lower if necessary
TOTAL_K = 50
CATEGORY_311_TOP_K = 40  # can be higher if necessary
CATEGORY_FACILITIES_TOP_K = 20
PLACE_RESULTS_TOP_K = 5
CLUSTER_TOPK = 5

SOURCE_COLUMNS = [
    "Created Date",
    "Problem (formerly Complaint Type)",
    "Problem Detail (formerly Descriptor)",
    "Latitude",
    "Longitude",
]

RENAMED_COLUMNS = {
    "Problem (formerly Complaint Type)": "Problem",
    "Problem Detail (formerly Descriptor)": "Problem Detail",
}

OUTPUT_COLUMNS = [
    "Created Date",
    "Problem",
    "Problem Detail",
    "Latitude",
    "Longitude",
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
    "latitude",
    "longitude",
]
