import faiss
import numpy as np
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

from embeddings import EmbeddingStore, _validate_metadata, _df_to_metadata, load_store


# ── EmbeddingStore ────────────────────────────────────────────────────────────

def test_embedding_store_len():
    store = EmbeddingStore(index=MagicMock(), movie_ids=["a", "b", "c"], metadata=[{}, {}, {}])
    assert len(store) == 3


def test_embedding_store_id_to_row_built_on_init():
    store = EmbeddingStore(index=MagicMock(), movie_ids=["x", "y", "z"], metadata=[{}, {}, {}])
    assert store.id_to_row == {"x": 0, "y": 1, "z": 2}


def test_embedding_store_empty():
    store = EmbeddingStore(index=MagicMock(), movie_ids=[], metadata=[])
    assert len(store) == 0
    assert store.id_to_row == {}


# ── _validate_metadata ────────────────────────────────────────────────────────

def test_validate_metadata_valid():
    _validate_metadata(pd.DataFrame({"id": [1], "title": ["Movie"]}))


def test_validate_metadata_missing_id():
    with pytest.raises(ValueError, match="missing required columns"):
        _validate_metadata(pd.DataFrame({"title": ["Movie"]}))


def test_validate_metadata_missing_title():
    with pytest.raises(ValueError, match="missing required columns"):
        _validate_metadata(pd.DataFrame({"id": [1]}))


def test_validate_metadata_missing_both():
    with pytest.raises(ValueError, match="missing required columns"):
        _validate_metadata(pd.DataFrame({"genre": ["Action"]}))


def test_validate_metadata_empty_df():
    with pytest.raises(ValueError, match="empty"):
        _validate_metadata(pd.DataFrame({"id": [], "title": []}))


# ── _df_to_metadata ───────────────────────────────────────────────────────────

def _base_df(**extra):
    data = {"id": ["1"], "title": ["Test Movie"]}
    data.update(extra)
    return pd.DataFrame(data)


def test_df_to_metadata_poster_url_built():
    df = _base_df(poster_path=["/abc.jpg"])
    result = _df_to_metadata(df)
    assert result[0]["poster_url"] == "https://image.tmdb.org/t/p/w500/abc.jpg"


def test_df_to_metadata_missing_poster_path_gives_none():
    df = _base_df(poster_path=[None])
    result = _df_to_metadata(df)
    assert result[0]["poster_url"] is None


def test_df_to_metadata_empty_poster_path_gives_none():
    df = _base_df(poster_path=[""])
    result = _df_to_metadata(df)
    assert result[0]["poster_url"] is None


def test_df_to_metadata_year_parsed():
    df = _base_df(release_date=["2021-06-15"])
    result = _df_to_metadata(df)
    assert result[0]["year"] == 2021


def test_df_to_metadata_year_none_for_missing_date():
    df = _base_df(release_date=[None])
    result = _df_to_metadata(df)
    assert result[0]["year"] is None


def test_df_to_metadata_year_none_for_non_numeric_date():
    df = _base_df(release_date=["unknown"])
    result = _df_to_metadata(df)
    assert result[0]["year"] is None


def test_df_to_metadata_preserves_other_columns():
    df = _base_df(genre=["Action"], overview=["Great film"])
    result = _df_to_metadata(df)
    assert result[0]["genre"] == "Action"
    assert result[0]["overview"] == "Great film"


def test_df_to_metadata_multiple_rows():
    df = pd.DataFrame({
        "id": ["1", "2"],
        "title": ["A", "B"],
        "release_date": ["2020-01-01", "2022-05-10"],
    })
    result = _df_to_metadata(df)
    assert len(result) == 2
    assert result[0]["year"] == 2020
    assert result[1]["year"] == 2022


# ── load_store ────────────────────────────────────────────────────────────────

def test_load_store_raises_for_missing_index(tmp_path):
    with pytest.raises(FileNotFoundError, match="FAISS index"):
        load_store(
            index_path=str(tmp_path / "missing.index"),
            metadata_path=str(tmp_path / "meta.parquet"),
        )


def test_load_store_raises_for_missing_metadata(tmp_path):
    index_path = tmp_path / "faiss.index"
    idx = faiss.IndexFlatIP(4)
    faiss.write_index(idx, str(index_path))

    with pytest.raises(FileNotFoundError, match="metadata"):
        load_store(
            index_path=str(index_path),
            metadata_path=str(tmp_path / "missing.parquet"),
        )


def test_load_store_returns_embedding_store(tmp_path):
    # Build a minimal but valid index + parquet
    dim = 4
    vecs = np.random.rand(3, dim).astype(np.float32)
    faiss.normalize_L2(vecs)
    idx = faiss.IndexFlatIP(dim)
    idx.add(vecs)
    index_path = tmp_path / "faiss.index"
    faiss.write_index(idx, str(index_path))

    df = pd.DataFrame({
        "id": ["1", "2", "3"],
        "title": ["A", "B", "C"],
        "release_date": ["2020-01-01", "2021-01-01", "2022-01-01"],
        "poster_path": ["/a.jpg", None, "/c.jpg"],
    })
    metadata_path = tmp_path / "metadata.parquet"
    df.to_parquet(metadata_path, index=False)

    store = load_store(index_path=str(index_path), metadata_path=str(metadata_path))
    assert len(store) == 3
    assert store.movie_ids == ["1", "2", "3"]
    assert store.id_to_row["2"] == 1
