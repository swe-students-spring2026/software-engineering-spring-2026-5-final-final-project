"""
This module provides utility for semantic search on 311 embeddings, edit the main function to test run.
"""

import numpy as np
import torch
from sentence_transformers import SentenceTransformer, util

from config import CATEGORY_TOP_K, EMBEDDINGS_MODEL
from embedding import load_311_categories, embed_311, load_facilities_categories, embed_facilities


def find_311_categories(query):
    """semantic search for the topk similar categories"""
    query = str(query.strip())

    categories = load_311_categories()
    embedded_category = torch.from_numpy(np.load(embed_311()))

    model = SentenceTransformer(
        EMBEDDINGS_MODEL,
        device="cpu", # needed for digitalocean
    )

    embedded_query = model.encode([query], normalize_embeddings=True)

    hits = util.semantic_search(
        embedded_query,
        embedded_category,
        top_k=min(CATEGORY_TOP_K, len(categories)),
    )[0]

    indexes = [hit["corpus_id"] for hit in hits]
    rows = categories.iloc[indexes]
    result = rows[["Problem", "Problem Detail"]].reset_index(drop=True)

    return result

def find_facilities_categories(query, clusters):
    """semantic search for the topk similar facility types from topk least problematic clusters from clustering"""
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
        top_k=min(CATEGORY_TOP_K, len(categories)),
    )[0]

    indexes = [hit["corpus_id"] for hit in hits]
    rows = categories.iloc[indexes]
    result = rows[["facgroup","facsubgrp","factype"]].reset_index(drop=True)

    return result
