import math


def _jaccard(set_a: set, set_b: set) -> float:
    union = len(set_a | set_b)
    return len(set_a & set_b) / union if union else 0.0


def _audio_similarity(feat_a: dict, feat_b: dict) -> float:
    vec_a = [feat_a["energy"], feat_a["valence"], feat_a["danceability"], feat_a["tempo"] / 250]
    vec_b = [feat_b["energy"], feat_b["valence"], feat_b["danceability"], feat_b["tempo"] / 250]

    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(x * x for x in vec_a))
    mag_b = math.sqrt(sum(x * x for x in vec_b))

    if mag_a == 0 or mag_b == 0:
        return 0.5

    return dot / (mag_a * mag_b)


def compute_score(user_a: dict, user_b: dict) -> float:
    sp_a = user_a.get("spotify") or {}
    sp_b = user_b.get("spotify") or {}

    genres_a = set(sp_a.get("top_genres") or [])
    genres_b = set(sp_b.get("top_genres") or [])
    genre_score = _jaccard(genres_a, genres_b)

    artists_a = {a.get("id") for a in (sp_a.get("top_artists") or []) if a.get("id")}
    artists_b = {a.get("id") for a in (sp_b.get("top_artists") or []) if a.get("id")}
    artist_score = _jaccard(artists_a, artists_b)

    feat_a = sp_a.get("audio_features")
    feat_b = sp_b.get("audio_features")
    audio_score = _audio_similarity(feat_a, feat_b) if feat_a and feat_b else 0.5

    return 0.50 * genre_score + 0.30 * artist_score + 0.20 * audio_score
