import numpy as np
import pytest
from unittest.mock import MagicMock

from recommender import Recommender, MovieResult


def _build_index(vectors: np.ndarray) -> MagicMock:
    """Mock FAISS IndexFlatIP backed by a real numpy matrix."""
    index = MagicMock()
    index.d = vectors.shape[1]

    def reconstruct(row, out):
        out[:] = vectors[row]

    def search(query, k):
        sims = (vectors @ query.T).flatten()
        top_k = min(k, len(sims))
        order = np.argsort(sims)[::-1][:top_k]
        return sims[order].reshape(1, -1), order.reshape(1, -1).astype(np.int64)

    index.reconstruct.side_effect = reconstruct
    index.search.side_effect = search
    return index


MOVIE_IDS = ["m1", "m2", "m3", "m4", "m5"]
METADATA = [
    {"title": "Alpha",   "genre": "Action"},
    {"title": "Beta",    "genre": "Drama"},
    {"title": "Gamma",   "genre": "Comedy"},
    {"title": "Delta",   "genre": "Thriller"},
    {"title": "Epsilon", "genre": "Sci-Fi"},
]
# Orthogonal unit vectors so similarities are predictable
VECTORS = np.array([
    [1.0, 0.0, 0.0, 0.0],
    [0.0, 1.0, 0.0, 0.0],
    [0.0, 0.0, 1.0, 0.0],
    [0.0, 0.0, 0.0, 1.0],
    [0.707, 0.707, 0.0, 0.0],
], dtype=np.float32)


@pytest.fixture
def rec():
    return Recommender(index=_build_index(VECTORS), movie_ids=MOVIE_IDS, metadata=METADATA)


def test_recommend_returns_movie_results(rec):
    results = rec.recommend(["m1"], k=3)
    assert len(results) == 3
    assert all(isinstance(r, MovieResult) for r in results)


def test_recommend_excludes_favorites(rec):
    favorites = ["m1", "m2"]
    results = rec.recommend(favorites, k=4)
    returned_ids = {r.movie_id for r in results}
    assert returned_ids.isdisjoint(favorites)


def test_recommend_empty_favorites_returns_empty(rec):
    assert rec.recommend([]) == []


def test_recommend_all_unknown_ids_returns_empty(rec):
    assert rec.recommend(["unknown1", "unknown2"]) == []


def test_recommend_partial_unknown_ids_still_works(rec):
    results = rec.recommend(["m1", "not_a_real_id"], k=2)
    assert len(results) == 2


def test_recommend_respects_k(rec):
    results = rec.recommend(["m1"], k=2)
    assert len(results) == 2


def test_recommend_result_fields(rec):
    result = rec.recommend(["m1"], k=1)[0]
    assert result.title != ""
    assert isinstance(result.similarity, float)
    assert isinstance(result.metadata, dict)


def test_recommend_similarity_ordering(rec):
    # m5 = [0.707, 0.707, 0, 0], m1 = [1, 0, 0, 0]
    # Taste profile from m1 alone → most similar should be m5 (shares x component)
    results = rec.recommend(["m1"], k=4)
    sims = [r.similarity for r in results]
    assert sims == sorted(sims, reverse=True)


def test_id_to_row_mapping(rec):
    assert rec._id_to_row["m1"] == 0
    assert rec._id_to_row["m5"] == 4


def test_average_and_normalize_produces_unit_vector(rec):
    vecs = np.array([[3.0, 4.0, 0.0, 0.0]], dtype=np.float32)
    result = rec._average_and_normalize(vecs)
    assert abs(np.linalg.norm(result) - 1.0) < 1e-5


def test_average_and_normalize_multiple_vecs(rec):
    vecs = np.array([
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
    ], dtype=np.float32)
    result = rec._average_and_normalize(vecs)
    assert abs(np.linalg.norm(result) - 1.0) < 1e-5
    # Average of two orthogonal unit vectors should point diagonally
    assert result[0, 0] > 0
    assert result[0, 1] > 0


def test_get_embeddings_shape(rec):
    vecs = rec._get_embeddings([0, 1, 2])
    assert vecs.shape == (3, 4)


def test_get_embeddings_correct_values(rec):
    vecs = rec._get_embeddings([0])
    np.testing.assert_array_almost_equal(vecs[0], VECTORS[0])
