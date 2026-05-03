"""
One-time preprocessing script.

Downloads the HuggingFace dataset, parses stringified embeddings → float32,
builds a FAISS IndexFlatIP, and saves the index + slim metadata to disk.

Run from the repo root:
    python recommendation-engine/scripts/preprocess.py

Outputs (gitignored):
    recommendation-engine/data/faiss.index       (~2.1 GB)
    recommendation-engine/data/metadata.parquet  (~200 MB)

Requires: datasets, pandas, pyarrow, faiss-cpu, numpy
"""

import json
import os
import sys
from pathlib import Path

import faiss
import numpy as np
import pandas as pd
from datasets import load_dataset

DATASET_NAME = "Remsky/Embeddings__Ultimate_1Million_Movies_Dataset"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data"
INDEX_PATH = OUTPUT_DIR / "faiss.index"
METADATA_PATH = OUTPUT_DIR / "metadata.parquet"

METADATA_COLUMNS = [
    "id",
    "title",
    "release_date",
    "genres",
    "director",
    "overview",
    "tagline",
    "imdb_rating",
    "vote_average",
    "poster_path",
    "movie_cast",
    "original_language",
]


def parse_embedding(raw: str) -> list[float] | None:
    """Parse a stringified JSON embedding array. Returns None on failure."""
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loading dataset: {DATASET_NAME}")
    dataset = load_dataset(DATASET_NAME, split="train")
    print(f"  {len(dataset):,} rows loaded")

    print("Parsing embeddings...")
    raw_embeddings = dataset["embedding"]
    parsed = [parse_embedding(e) for e in raw_embeddings]

    # Filter out rows where embedding parsing failed
    valid_mask = [e is not None for e in parsed]
    skipped = valid_mask.count(False)
    if skipped:
        print(f"  Skipping {skipped:,} rows with unparseable embeddings")

    valid_indices = [i for i, ok in enumerate(valid_mask) if ok]
    embeddings = np.array(
        [parsed[i] for i in valid_indices], dtype=np.float32
    )
    print(f"  Embedding matrix shape: {embeddings.shape}")

    print("Normalising vectors (L2) for cosine similarity via inner product...")
    faiss.normalize_L2(embeddings)

    dim = embeddings.shape[1]
    print(f"Building FAISS IndexFlatIP (dim={dim})...")
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    print(f"  Index contains {index.ntotal:,} vectors")

    print(f"Saving index to {INDEX_PATH} ...")
    faiss.write_index(index, str(INDEX_PATH))

    print("Building metadata dataframe...")
    df = dataset.to_pandas().iloc[valid_indices].reset_index(drop=True)

    # Keep only the columns we need at serve time
    keep = [c for c in METADATA_COLUMNS if c in df.columns]
    df = df[keep].copy()

    # Add a row_index column so the rec engine can map FAISS row → metadata
    df["row_index"] = range(len(df))

    print(f"Saving metadata to {METADATA_PATH} ...")
    df.to_parquet(METADATA_PATH, index=False)

    index_mb = INDEX_PATH.stat().st_size / 1024 / 1024
    meta_mb = METADATA_PATH.stat().st_size / 1024 / 1024
    print(
        f"\nDone.\n"
        f"  faiss.index:       {index_mb:,.0f} MB\n"
        f"  metadata.parquet:  {meta_mb:,.0f} MB\n"
        f"  Movies indexed:    {index.ntotal:,}"
    )


if __name__ == "__main__":
    main()
