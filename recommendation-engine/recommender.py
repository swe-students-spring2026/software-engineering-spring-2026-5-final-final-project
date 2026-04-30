import numpy as np
import faiss
from dataclasses import dataclass


@dataclass
class MovieResult:
    movie_id: str
    title: str
    similarity: float
    metadata: dict


class Recommender:
    def __init__(self, index: faiss.Index, movie_ids: list[str], metadata: list[dict]):
        """
        index:     FAISS index built with L2-normalized embeddings (inner product = cosine)
        movie_ids: list of movie IDs in the same order as rows in the index
        metadata:  list of dicts (title, year, genre, etc.) parallel to movie_ids
        """
        self.index = index
        self.movie_ids = movie_ids
        self.metadata = metadata
        self._id_to_row = {mid: i for i, mid in enumerate(movie_ids)}

    def recommend(self, favorite_ids: list[str], k: int = 20) -> list[MovieResult]:
        """
        Given up to 4 favorite movie IDs, return k recommendations ranked by cosine similarity.
        Input movies are excluded from results. Unknown IDs are silently skipped.
        """
        rows = [self._id_to_row[mid] for mid in favorite_ids if mid in self._id_to_row]
        if not rows:
            return []

        embeddings = self._get_embeddings(rows)
        taste_profile = self._average_and_normalize(embeddings)

        # Fetch extra candidates to account for filtering out input movies
        fetch_k = k + len(favorite_ids)
        similarities, indices = self.index.search(taste_profile, fetch_k)

        exclude = set(favorite_ids)
        results = []
        for sim, idx in zip(similarities[0], indices[0]):
            if idx < 0:
                continue
            mid = self.movie_ids[idx]
            if mid in exclude:
                continue
            results.append(MovieResult(
                movie_id=mid,
                title=self.metadata[idx].get("title", ""),
                similarity=float(sim),
                metadata=self.metadata[idx],
            ))
            if len(results) == k:
                break

        return results

    def _get_embeddings(self, rows: list[int]) -> np.ndarray:
        # FAISS IndexFlat stores vectors contiguously; reconstruct by row index
        dim = self.index.d
        vecs = np.empty((len(rows), dim), dtype=np.float32)
        for i, row in enumerate(rows):
            self.index.reconstruct(row, vecs[i])
        return vecs

    def _average_and_normalize(self, embeddings: np.ndarray) -> np.ndarray:
        avg = embeddings.mean(axis=0, keepdims=True).astype(np.float32)
        faiss.normalize_L2(avg)
        return avg
