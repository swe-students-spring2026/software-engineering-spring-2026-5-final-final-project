"""
This module provides functions to load, builds and saves category embeddings for 311 search.
"""

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

from config import (
    EMBEDDINGS_311_PATH,
    EMBEDDINGS_MODEL,
    PROCESSED_311_PATH,
)


def load_311_categories():
    """Load categories from cleaned dataset"""
    categories = pd.read_csv(
        PROCESSED_311_PATH,
        usecols=["Problem", "Problem Detail"],
    ).dropna()
    categories["Problem"] = categories["Problem"].astype(str).str.strip()
    categories["Problem Detail"] = categories["Problem Detail"].astype(str).str.strip()
    categories = categories.drop_duplicates().reset_index(drop=True)
    categories["text"] = categories["Problem"] + " " + categories["Problem Detail"]
    return categories


def embed_311():
    """Embed the categories"""
    if EMBEDDINGS_311_PATH.exists():
        return EMBEDDINGS_311_PATH

    categories = load_311_categories()
    model = SentenceTransformer(EMBEDDINGS_MODEL, device="cpu")

    embeddings = model.encode(categories["text"].tolist(), normalize_embeddings=True)
    np.save(EMBEDDINGS_311_PATH, embeddings)
    return EMBEDDINGS_311_PATH


def load_facilities_categories(clusters):
    """Load facilitities' categories from clusters from clustering logic"""
    rows = []

    for c in clusters:
        for facility in getattr(c, "facilities", []):
            rows.append([facility[1], facility[2], facility[3]])

    categories = pd.DataFrame(rows, columns=["facgroup", "facsubgrp", "factype"])

    if categories.empty:
        categories = pd.DataFrame(columns=["facgroup", "facsubgrp", "factype"])

    categories["facgroup"] = categories["facgroup"].astype(str).str.strip()
    categories["facsubgrp"] = categories["facsubgrp"].astype(str).str.strip()
    categories["factype"] = categories["factype"].astype(str).str.strip()
    categories = categories.drop_duplicates().reset_index(drop=True)
    categories["text"] = (
        categories["facgroup"]
        + " "
        + categories["facsubgrp"]
        + " "
        + categories["factype"]
    )
    return categories


def embed_facilities(clusters):
    """Embed the facilities' categories"""
    categories = load_facilities_categories(clusters)
    model = SentenceTransformer(EMBEDDINGS_MODEL, device="cpu")

    return model.encode(categories["text"].tolist(), normalize_embeddings=True)


def load_facility_names(clusters):
    """Load facilitities' names"""
    rows = []

    for c in clusters:
        for facility in c.facilities:
            if len(facility) < 3:
                continue

            rows.append([facility[0], facility[2]])

    names = pd.DataFrame(rows, columns=["facname", "facsubgrp"])

    if names.empty:
        names = pd.DataFrame(columns=["facname", "facsubgrp", "text"])
        return names

    names["facname"] = names["facname"].astype(str).str.strip()
    names["facsubgrp"] = (
        names["facsubgrp"].astype(str).str.strip()
    )  # this to avoid noise
    names["text"] = names["facname"] + " " + names["facsubgrp"]
    return names


def embed_facility_names(facility_names):
    """Embed the facilities' names"""
    model = SentenceTransformer(EMBEDDINGS_MODEL, device="cpu")

    return model.encode(facility_names["text"].tolist(), normalize_embeddings=True)
