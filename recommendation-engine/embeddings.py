"""
Loads the pre-built FAISS index and metadata parquet into memory at startup.

Expected env vars (with defaults):
    INDEX_PATH    path to faiss.index        (default: data/faiss.index)
    METADATA_PATH path to metadata.parquet   (default: data/metadata.parquet)

Usage:
    from embeddings import load_store, EmbeddingStore

    store = load_store()          # call once at app startup
    store.index                   # faiss.Index
    store.movie_ids               # list[str]  — parallel to index rows
    store.metadata                # list[dict] — parallel to index rows
    store.id_to_row               # dict[str, int]
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

import faiss
import pandas as pd


@dataclass
class EmbeddingStore:
    index: faiss.Index
    movie_ids: list[str]
    metadata: list[dict]
    id_to_row: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.id_to_row = {mid: i for i, mid in enumerate(self.movie_ids)}

    def __len__(self) -> int:
        return len(self.movie_ids)


def load_store(
    index_path: str | None = None,
    metadata_path: str | None = None,
) -> EmbeddingStore:
    """
    Load the FAISS index and metadata from disk.
    Paths are resolved from env vars, then explicit args, then defaults.
    """
    index_path = index_path or os.getenv("INDEX_PATH", "data/faiss.index")
    metadata_path = metadata_path or os.getenv(
        "METADATA_PATH", "data/metadata.parquet"
    )

    _check_exists(index_path, "FAISS index")
    _check_exists(metadata_path, "metadata parquet")

    index = faiss.read_index(str(index_path))

    df = pd.read_parquet(metadata_path)
    _validate_metadata(df)

    movie_ids = df["id"].astype(str).tolist()
    metadata = _df_to_metadata(df)

    return EmbeddingStore(index=index, movie_ids=movie_ids, metadata=metadata)


# ── helpers ──────────────────────────────────────────────────────────────────

def _check_exists(path: str, label: str) -> None:
    if not Path(path).exists():
        raise FileNotFoundError(
            f"{label} not found at '{path}'. "
            "Run scripts/preprocess.py first to generate the data files."
        )


def _validate_metadata(df: pd.DataFrame) -> None:
    required = {"id", "title"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"metadata.parquet is missing required columns: {missing}")
    if len(df) == 0:
        raise ValueError("metadata.parquet is empty")


def _df_to_metadata(df: pd.DataFrame) -> list[dict]:
    """Convert dataframe to list of lean dicts, building poster_url from poster_path."""
    TMDB_BASE = "https://image.tmdb.org/t/p/w500"
    records = []
    for row in df.itertuples(index=False):
        d = row._asdict()

        # Build poster_url from TMDB poster_path
        poster_path = d.get("poster_path") or ""
        d["poster_url"] = f"{TMDB_BASE}{poster_path}" if poster_path else None

        # Normalise year from release_date (YYYY-MM-DD)
        release_date = str(d.get("release_date") or "")
        d["year"] = int(release_date[:4]) if release_date[:4].isdigit() else None

        records.append(d)
    return records
