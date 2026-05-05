"""
Recommendation-engine HTTP service.

Wraps the FAISS index + metadata in a Flask app exposing the endpoints the
frontend's api_client expects. Loads everything once at startup; all requests
are served from in-memory data structures.

Run locally:
    python recommendation-engine/app.py

Run in production:
    gunicorn -w 1 -b 0.0.0.0:8000 app:app
    # workers must be 1 — FAISS index is multi-GB; use threads for concurrency:
    #   gunicorn -w 1 --threads 8 -b 0.0.0.0:8000 app:app

Configuration (env vars):
    INDEX_PATH        path to faiss.index
    METADATA_PATH     path to metadata.parquet
    EMBED_MODEL_NAME  HuggingFace model id for query encoding
                      (default: nomic-ai/nomic-embed-text-v1.5)
    NOMIC_QUERY_PREFIX  prefix prepended to user queries before encoding
                        (default: "search_query: " — must match how the dataset
                        was indexed; check the dataset card)
"""

import logging
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import numpy as np
from flask import Flask, jsonify, request

from embeddings import load_store
from recommender import Recommender

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

EMBED_MODEL_NAME = os.getenv(
    "EMBED_MODEL_NAME", "nomic-ai/nomic-embed-text-v1.5")
NOMIC_QUERY_PREFIX = os.getenv("NOMIC_QUERY_PREFIX", "")
DEFAULT_K = 20

app = Flask(__name__)

# ── lazy globals, populated at startup ───────────────────────────────────────
_store = None
_recommender = None
_encoder = None
_title_index: dict[str, int] = {}


def _init() -> None:
    """Load index, metadata, encoder, and build the title → row lookup."""
    global _store, _recommender, _encoder, _title_index

    log.info("Loading embedding store…")
    _store = load_store()
    log.info("  %d movies loaded (dim=%d)", len(_store), _store.index.d)

    _recommender = Recommender(
        index=_store.index,
        movie_ids=_store.movie_ids,
        metadata=_store.metadata,
    )

    log.info("Building title index…")
    _title_index = {
        (m.get("title") or "").strip().lower(): row
        for row, m in enumerate(_store.metadata)
        if m.get("title")
    }

    log.info("Loading sentence encoder: %s", EMBED_MODEL_NAME)
    from sentence_transformers import SentenceTransformer

    # Nomic's model is hosted with custom code on HF; trust_remote_code is required.
    _encoder = SentenceTransformer(
        EMBED_MODEL_NAME, trust_remote_code=True, device="cpu")


    # Sanity check: query encoding must produce vectors of the same dim as the index
    test_vec = _encoder.encode(
        [NOMIC_QUERY_PREFIX + "test"], convert_to_numpy=True)
    if test_vec.shape[1] != _store.index.d:
        raise RuntimeError(
            f"Embedding dim mismatch: encoder produces {test_vec.shape[1]}-dim vectors "
            f"but FAISS index expects {_store.index.d}. Wrong EMBED_MODEL_NAME?"
        )

    log.info("Service ready.")


# ── helpers ──────────────────────────────────────────────────────────────────

def _movie_dict(row: int, *, similarity: float | None = None) -> dict:
    meta = _store.metadata[row]
    movie_id = _store.movie_ids[row]

    genres = meta.get("genres") or ""
    if isinstance(genres, list):
        genres = ", ".join(genres)

    out = {
        "id": movie_id,
        "title": meta.get("title", ""),
        "description": meta.get("overview") or meta.get("tagline") or "",
        "genre": genres,
        "year": meta.get("year"),
        "rating": meta.get("imdb_rating") or meta.get("vote_average"),
        "poster_url": meta.get("poster_url"),
    }
    if similarity is not None:
        out["similarity"] = round(float(similarity), 4)
    return out


def _movie_detail(row: int) -> dict:
    meta = _store.metadata[row]
    base = _movie_dict(row)

    cast = meta.get("movie_cast") or []
    if isinstance(cast, str):
        cast = [c.strip() for c in cast.split(",") if c.strip()]

    return {
        **base,
        "director": meta.get("director", ""),
        "cast": cast[:10],
    }


def _resolve_title_to_id(title: str) -> str | None:
    row = _title_index.get(title.strip().lower())
    return _store.movie_ids[row] if row is not None else None


def _encode_query(text: str) -> np.ndarray:
    """Encode a user query into a unit-length vector matching the index.

    Nomic Embed requires the 'search_query: ' prefix for query-side text;
    documents in the dataset were encoded with 'search_document: '.
    """
    prefixed = NOMIC_QUERY_PREFIX + text
    vec = _encoder.encode([prefixed], convert_to_numpy=True).astype(np.float32)
    import faiss
    faiss.normalize_L2(vec)
    return vec


# ── routes ───────────────────────────────────────────────────────────────────


@app.get("/health")
def health():
    return jsonify(status="ok", movies=len(_store) if _store else 0)


@app.get("/search")
def search():
    query = request.args.get("q", "").strip()
    mode = request.args.get("mode", "direct")
    if not query:
        return jsonify(results=[])
    if mode == "intent":
        return jsonify(results=_semantic_search(query, k=DEFAULT_K))
    return jsonify(results=_title_search(query, k=DEFAULT_K))


@app.post("/recommend")
def recommend():
    body = request.get_json(silent=True) or {}
    titles = body.get("favorite_titles") or []
    if not titles:
        return jsonify(results=[])

    favorite_ids = [mid for mid in (_resolve_title_to_id(t)
                                    for t in titles) if mid]
    if not favorite_ids:
        return jsonify(results=[])

    results = _recommender.recommend(favorite_ids, k=DEFAULT_K)
    return jsonify(
        results=[
            {**_movie_dict(_store.id_to_row[r.movie_id]),
             "similarity": round(r.similarity, 4)}
            for r in results
        ]
    )


@app.get("/movies/<movie_id>")
def movie_detail(movie_id):
    row = _store.id_to_row.get(movie_id)
    if row is None:
        return jsonify(error="not found"), 404
    return jsonify(_movie_detail(row))


@app.get("/movies/<movie_id>/similar")
def similar(movie_id):
    if movie_id not in _store.id_to_row:
        return jsonify(error="not found"), 404
    results = _recommender.recommend([movie_id], k=DEFAULT_K)
    return jsonify(
        results=[
            {**_movie_dict(_store.id_to_row[r.movie_id]),
             "similarity": round(r.similarity, 4)}
            for r in results
        ]
    )


@app.post("/movies/batch")
def movies_batch():
    body = request.get_json(silent=True) or {}
    ids = body.get("ids") or []
    results = []
    for mid in ids:
        row = _store.id_to_row.get(mid)
        if row is not None:
            results.append(_movie_dict(row))
    return jsonify(results=results)


# ── search implementations ───────────────────────────────────────────────────


def _title_search(query: str, k: int) -> list[dict]:
    needle = query.lower()
    matches = []
    for row, m in enumerate(_store.metadata):
        title = (m.get("title") or "").lower()
        if needle in title:
            matches.append((row, title))
            if len(matches) >= k * 4:
                break
    matches.sort(key=lambda x: (x[1] != needle,
                 not x[1].startswith(needle), x[1]))
    return [_movie_dict(row) for row, _ in matches[:k]]


def _semantic_search(query: str, k: int) -> list[dict]:
    qvec = _encode_query(query)
    sims, idxs = _store.index.search(qvec, k)
    out = []
    for sim, row in zip(sims[0], idxs[0]):
        if row < 0:
            continue
        out.append(_movie_dict(int(row), similarity=float(sim)))
    return out


# ── startup ──────────────────────────────────────────────────────────────────

_init()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
