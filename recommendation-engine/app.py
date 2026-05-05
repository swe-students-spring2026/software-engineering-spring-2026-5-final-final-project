import os
import json
from typing import Any

from dotenv import load_dotenv
from flask import Flask, jsonify, request

from embeddings import load_store
from recommender import Recommender

load_dotenv()

app = Flask(__name__)

# ── load data at startup ──────────────────────────────────────────────────────
store = load_store()
recommender = Recommender(store.index, store.movie_ids, store.metadata)

DEFAULT_PORT = int(os.getenv("RECOMMENDATION_PORT", "5001"))


# ── helpers ───────────────────────────────────────────────────────────────────

def _is_nan(val: Any) -> bool:
    """Check if a value is NaN (float nan) or the string 'nan'."""
    if val is None:
        return True
    if isinstance(val, float):
        return val != val  # NaN is the only value that != itself
    if isinstance(val, str):
        return val.strip().lower() == "nan"
    return False


def _clean_str(val: Any, default: str = "") -> str:
    if _is_nan(val):
        return default
    s = str(val).strip()
    return s if s and s.lower() != "nan" else default


def _normalize_genres(raw: Any) -> str:
    """Convert various genre formats to a plain comma-separated string."""
    if _is_nan(raw):
        return ""
    if isinstance(raw, str):
        stripped = raw.strip()
        if not stripped or stripped.lower() == "nan":
            return ""
        # Try JSON array of objects or strings
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, list):
                parts = []
                for item in parsed:
                    if isinstance(item, dict):
                        parts.append(str(item.get("name") or item.get("genre") or ""))
                    else:
                        parts.append(str(item))
                return ", ".join(p for p in parts if p)
        except (json.JSONDecodeError, TypeError):
            pass
        # Pipe-separated or plain string
        if "|" in stripped:
            return ", ".join(g.strip() for g in stripped.split("|") if g.strip())
        return stripped
    if isinstance(raw, list):
        parts = []
        for item in raw:
            if isinstance(item, dict):
                parts.append(str(item.get("name") or item.get("genre") or ""))
            else:
                parts.append(str(item))
        return ", ".join(p for p in parts if p)
    return str(raw)


def _normalize_cast(raw: Any) -> list[str]:
    """Convert various cast formats to a list of actor names."""
    if _is_nan(raw):
        return []
    if isinstance(raw, str):
        stripped = raw.strip()
        if not stripped or stripped.lower() == "nan":
            return []
        # Try JSON array
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, list):
                return [_clean_str(x) for x in parsed if _clean_str(x)]
        except (json.JSONDecodeError, TypeError):
            pass
        # Comma-separated or pipe-separated
        for sep in (", ", ",", "|"):
            if sep in stripped:
                return [x.strip() for x in stripped.split(sep) if x.strip() and x.strip().lower() != "nan"]
        return [stripped]
    if isinstance(raw, list):
        return [_clean_str(x) for x in raw if _clean_str(x)]
    s = _clean_str(raw)
    return [s] if s else []


def _metadata_to_dict(row_idx: int, meta: dict, include_similarity: bool = False, similarity: float | None = None) -> dict:
    """Normalize a metadata record to the shape the frontend templates expect."""
    raw_rating = meta.get("vote_average") or meta.get("imdb_rating") or 0.0
    try:
        rating = float(raw_rating)
        if rating != rating:  # NaN check
            rating = 0.0
    except (TypeError, ValueError):
        rating = 0.0

    poster_path = meta.get("poster_path")
    poster_url = meta.get("poster_url")
    if _is_nan(poster_path) or _is_nan(poster_url):
        poster_url = None

    result = {
        "id": _clean_str(meta.get("id")),
        "title": _clean_str(meta.get("title")),
        "description": _clean_str(meta.get("overview") or meta.get("tagline"), default=""),
        "genre": _normalize_genres(meta.get("genres")),
        "year": meta.get("year") if not _is_nan(meta.get("year")) else None,
        "rating": rating,
        "poster_url": poster_url,
        "director": _clean_str(meta.get("director"), default="Unknown"),
        "cast": _normalize_cast(meta.get("movie_cast")),
    }
    if include_similarity and similarity is not None:
        result["similarity"] = round(similarity, 4)
    return result


def _titles_to_ids(titles: list[str]) -> list[str]:
    """Map user-provided titles to movie IDs via substring search."""
    ids = []
    for title in titles:
        title_clean = title.strip().lower()
        if not title_clean:
            continue
        matched_id = None
        # prefer exact case-insensitive match
        for mid, meta in zip(store.movie_ids, store.metadata):
            meta_title = str(meta.get("title", "")).strip()
            if meta_title.lower() == title_clean:
                matched_id = mid
                break
        # fallback to substring match
        if matched_id is None:
            for mid, meta in zip(store.movie_ids, store.metadata):
                meta_title = str(meta.get("title", "")).strip()
                if title_clean in meta_title.lower():
                    matched_id = mid
                    break
        if matched_id:
            ids.append(matched_id)
    return ids


# ── routes ────────────────────────────────────────────────────────────────────

@app.route("/recommend", methods=["POST"])
def recommend():
    data = request.get_json(silent=True) or {}
    favorite_ids = data.get("favorite_ids", [])
    favorite_titles = data.get("favorite_titles", [])
    k = data.get("k", 20)

    try:
        k = int(k)
    except (TypeError, ValueError):
        k = 20

    if favorite_titles and not favorite_ids:
        favorite_ids = _titles_to_ids(favorite_titles)

    if not favorite_ids:
        return jsonify([])

    results = recommender.recommend(favorite_ids, k=k)
    return jsonify([
        _metadata_to_dict(store.id_to_row[r.movie_id], r.metadata, include_similarity=True, similarity=r.similarity)
        for r in results
    ])


@app.route("/search")
def search():
    query = request.args.get("q", "").strip().lower()
    if not query:
        return jsonify([])

    matches = []
    for i, meta in enumerate(store.metadata):
        title = str(meta.get("title", "")).lower()
        overview = str(meta.get("overview") or "").lower()
        genres = str(meta.get("genres") or "").lower()
        if query in title or query in overview or query in genres:
            matches.append(_metadata_to_dict(i, meta))
            if len(matches) >= 20:
                break
    return jsonify(matches)


@app.route("/movies/<movie_id>")
def movie_detail(movie_id):
    row = store.id_to_row.get(movie_id)
    if row is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(_metadata_to_dict(row, store.metadata[row]))


@app.route("/movies/<movie_id>/similar")
def similar_movies(movie_id):
    row = store.id_to_row.get(movie_id)
    if row is None:
        return jsonify({"error": "Not found"}), 404
    results = recommender.recommend([movie_id], k=4)
    return jsonify([
        _metadata_to_dict(store.id_to_row[r.movie_id], r.metadata, include_similarity=True, similarity=r.similarity)
        for r in results
    ])


@app.route("/movies/by-ids", methods=["POST"])
def movies_by_ids():
    data = request.get_json(silent=True) or {}
    movie_ids = data.get("movie_ids", [])
    results = []
    for mid in movie_ids:
        row = store.id_to_row.get(mid)
        if row is not None:
            results.append(_metadata_to_dict(row, store.metadata[row]))
    return jsonify(results)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=DEFAULT_PORT)
