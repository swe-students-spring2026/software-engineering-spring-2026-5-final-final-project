"""
This module provides functions to load, builds and saves category embeddings for 311 search.
"""

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

from config import EMBEDDINGS_PATH, PROCESSED_311_PATH, EMBEDDINGS_MODEL


def load_categories():
    """placeholder"""
    categories = pd.read_csv(
        PROCESSED_311_PATH,
        usecols=["Problem", "Problem Detail"],
    ).dropna()
    categories["Problem"] = categories["Problem"].astype(str).str.strip()
    categories["Problem Detail"] = categories["Problem Detail"].astype(str).str.strip()
    categories = categories.drop_duplicates().reset_index(drop=True)
    categories["text"] = categories["Problem"] + " " + categories["Problem Detail"]
    return categories


def embed():
    """placeholder"""
    if EMBEDDINGS_PATH.exists():
        return EMBEDDINGS_PATH

    categories = load_categories()
    model = SentenceTransformer(EMBEDDINGS_MODEL, device="cpu")

    embeddings = model.encode(categories["text"].tolist(), normalize_embeddings=True)
    np.save(EMBEDDINGS_PATH, embeddings)
    return EMBEDDINGS_PATH
