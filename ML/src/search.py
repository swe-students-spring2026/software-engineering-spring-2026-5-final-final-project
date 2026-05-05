"""
This module provides utility for semantic search on 311 embeddings, edit the main function to test run.
"""

import numpy as np
import torch
from sentence_transformers import SentenceTransformer, util

from config import CATEGORY_311_TOP_K, CATEGORY_FACILITIES_TOP_K, EMBEDDINGS_MODEL
from embedding import (
    load_311_categories,
    embed_311,
    load_facilities_categories,
    embed_facilities,
    load_facility_names,
    embed_facility_names,
)


def find_311_categories(query):
    """Find topk most similar 311 categories"""
    query = str(query.strip())

    categories = load_311_categories()
    embedded_category = torch.from_numpy(np.load(embed_311()))

    model = SentenceTransformer(
        EMBEDDINGS_MODEL,
        device="cpu",  # needed for digitalocean
    )

    embedded_query = model.encode([query], normalize_embeddings=True)

    hits = util.semantic_search(
        embedded_query,
        embedded_category,
        top_k=min(CATEGORY_311_TOP_K, len(categories)),
    )[0]

    indexes = [hit["corpus_id"] for hit in hits]
    rows = categories.iloc[indexes]
    result = rows[["Problem", "Problem Detail"]].reset_index(drop=True)

    return result


def find_facilities_categories(query, clusters):
    """Find topk most similar facilities' categories"""

    query = str(query.strip())

    categories = load_facilities_categories(clusters)
    embedded_category = torch.from_numpy(embed_facilities(clusters))

    model = SentenceTransformer(
        EMBEDDINGS_MODEL,
        device="cpu",
    )

    embedded_query = model.encode([query], normalize_embeddings=True)

    hits = util.semantic_search(
        embedded_query,
        embedded_category,
        top_k=min(CATEGORY_FACILITIES_TOP_K, len(categories)),
    )[0]

    indexes = [hit["corpus_id"] for hit in hits]
    rows = categories.iloc[indexes]
    result = rows[["facgroup", "facsubgrp", "factype"]].reset_index(drop=True)

    return result


def find_facility_name_scores(query, clusters):
    """Find facilities simililarity with user querey, mapped by indexes"""
    query = str(query.strip())
    facility_names = load_facility_names(clusters)
    facility_positions = []

    for cluster_index, c in enumerate(clusters):
        for facility_index in range(len(c.facilities)):
            facility_positions.append((cluster_index, facility_index))

    embedded_names = torch.from_numpy(embed_facility_names(facility_names))

    model = SentenceTransformer(
        EMBEDDINGS_MODEL,
        device="cpu",
    )

    embedded_query = model.encode([query], normalize_embeddings=True)

    hits = util.semantic_search(
        embedded_query,
        embedded_names,
        top_k=len(facility_names),
    )[0]

    results = []
    for hit in hits:
        cluster_index, facility_index = facility_positions[hit["corpus_id"]]
        results.append(
            {
                "cluster_index": cluster_index,
                "facility_index": facility_index,
                "score": float(hit["score"]),
            }
        )

    return results
