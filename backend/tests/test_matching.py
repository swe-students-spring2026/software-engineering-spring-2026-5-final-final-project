"""
Tests for app/services/matching.py.

Pure functions — no I/O, no mocks needed.
Covers: _jaccard, _audio_similarity, compute_score (all branches).
"""

import math
import pytest

from app.services.matching import _audio_similarity, _jaccard, compute_score


# ===========================================================================
# _jaccard
# ===========================================================================

class TestJaccard:
    def test_identical_sets(self):
        assert _jaccard({"a", "b", "c"}, {"a", "b", "c"}) == pytest.approx(1.0)

    def test_disjoint_sets(self):
        assert _jaccard({"a", "b"}, {"c", "d"}) == pytest.approx(0.0)

    def test_partial_overlap(self):
        # intersection=1, union=3 → 1/3
        assert _jaccard({"a", "b"}, {"b", "c"}) == pytest.approx(1 / 3)

    def test_both_empty(self):
        assert _jaccard(set(), set()) == pytest.approx(0.0)

    def test_one_empty(self):
        assert _jaccard({"a"}, set()) == pytest.approx(0.0)
        assert _jaccard(set(), {"a"}) == pytest.approx(0.0)

    def test_single_common_element(self):
        assert _jaccard({"x"}, {"x"}) == pytest.approx(1.0)

    def test_subset(self):
        # intersection=2, union=3 → 2/3
        assert _jaccard({"a", "b"}, {"a", "b", "c"}) == pytest.approx(2 / 3)


# ===========================================================================
# _audio_similarity
# ===========================================================================

def _feat(energy=0.5, valence=0.5, danceability=0.5, tempo=125.0):
    return {"energy": energy, "valence": valence, "danceability": danceability, "tempo": tempo}


class TestAudioSimilarity:
    def test_identical_features_return_one(self):
        f = _feat()
        assert _audio_similarity(f, f) == pytest.approx(1.0)

    def test_zero_vector_returns_half(self):
        zero = {"energy": 0.0, "valence": 0.0, "danceability": 0.0, "tempo": 0.0}
        assert _audio_similarity(zero, _feat()) == pytest.approx(0.5)
        assert _audio_similarity(_feat(), zero) == pytest.approx(0.5)

    def test_result_between_zero_and_one(self):
        a = _feat(energy=0.9, valence=0.1, danceability=0.8, tempo=160.0)
        b = _feat(energy=0.2, valence=0.9, danceability=0.3, tempo=80.0)
        result = _audio_similarity(a, b)
        assert 0.0 <= result <= 1.0

    def test_symmetry(self):
        a = _feat(energy=0.8, valence=0.3, danceability=0.6, tempo=120.0)
        b = _feat(energy=0.4, valence=0.7, danceability=0.5, tempo=100.0)
        assert _audio_similarity(a, b) == pytest.approx(_audio_similarity(b, a))

    def test_tempo_scaled_by_250(self):
        # Two features differing only in tempo=250 vs tempo=0
        # tempo/250 normalises to 1.0 vs 0.0
        a = {"energy": 0.0, "valence": 0.0, "danceability": 0.0, "tempo": 250.0}
        b = {"energy": 0.0, "valence": 0.0, "danceability": 0.0, "tempo": 0.0}
        # Both vectors are [0,0,0,1] and [0,0,0,0] — second has zero magnitude
        assert _audio_similarity(a, b) == pytest.approx(0.5)


# ===========================================================================
# compute_score
# ===========================================================================

def _user(genres=None, artist_ids=None, audio=None):
    return {
        "spotify": {
            "top_genres": genres or [],
            "top_artists": [{"id": aid, "name": aid} for aid in (artist_ids or [])],
            "audio_features": audio,
        }
    }


class TestComputeScore:
    def test_perfect_match_genres_and_artists_no_audio(self):
        u = _user(genres=["pop", "rock"], artist_ids=["a1", "a2"])
        score = compute_score(u, u)
        # genre=1.0, artist=1.0, audio=0.5 (missing) → 0.5+0.3+0.1=0.9
        assert score == pytest.approx(0.90)

    def test_no_overlap_returns_audio_fallback(self):
        a = _user(genres=["pop"], artist_ids=["a1"])
        b = _user(genres=["jazz"], artist_ids=["b1"])
        # genre=0, artist=0, audio=0.5 → 0+0+0.1=0.1
        assert compute_score(a, b) == pytest.approx(0.10)

    def test_audio_features_used_when_both_present(self):
        feat = {"energy": 0.8, "valence": 0.6, "danceability": 0.7, "tempo": 120.0}
        a = _user(audio=feat)
        b = _user(audio=feat)
        # identical audio → audio_score=1.0; genre=0, artist=0 → 0+0+0.2=0.2
        assert compute_score(a, b) == pytest.approx(0.20)

    def test_audio_fallback_when_one_missing(self):
        feat = {"energy": 0.5, "valence": 0.5, "danceability": 0.5, "tempo": 125.0}
        a = _user(audio=feat)
        b = _user(audio=None)
        score = compute_score(a, b)
        # audio_score defaults to 0.5 → contributes 0.1
        assert score == pytest.approx(0.10)

    def test_no_spotify_data_returns_audio_fallback_only(self):
        assert compute_score({}, {}) == pytest.approx(0.10)

    def test_score_weights_sum(self):
        # 50% genre + 30% artist + 20% audio
        genres = ["g1", "g2", "g3"]
        artists = ["a1", "a2"]
        feat = {"energy": 1.0, "valence": 1.0, "danceability": 1.0, "tempo": 250.0}
        u = _user(genres=genres, artist_ids=artists, audio=feat)
        assert compute_score(u, u) == pytest.approx(1.0)

    def test_partial_genre_overlap(self):
        a = _user(genres=["pop", "rock", "indie"])
        b = _user(genres=["pop", "jazz"])
        # intersection=1, union=4 → jaccard=0.25; artist=0; audio=0.5
        # 0.5*0.25 + 0 + 0.2*0.5 = 0.125 + 0.1 = 0.225
        assert compute_score(a, b) == pytest.approx(0.225)

    def test_score_is_float_between_zero_and_one(self):
        a = _user(genres=["pop"], artist_ids=["a1"],
                  audio={"energy": 0.5, "valence": 0.5, "danceability": 0.5, "tempo": 120.0})
        b = _user(genres=["rock"], artist_ids=["b1"],
                  audio={"energy": 0.8, "valence": 0.2, "danceability": 0.4, "tempo": 90.0})
        score = compute_score(a, b)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
