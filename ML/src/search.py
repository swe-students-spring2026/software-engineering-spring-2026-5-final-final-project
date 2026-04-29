"""
This module provides utility for semantic search on 311 embeddings, edit the main function to test run.
"""

import numpy as np
import torch
from sentence_transformers import SentenceTransformer, util

from config import CATEGORY_TOP_K, EMBEDDINGS_MODEL
from embedding import load_categories, embed


def find_categories(query):
    """placeholder"""
    query = str(query.strip())

    categories = load_categories()
    embedded_category = torch.from_numpy(np.load(embed()))

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