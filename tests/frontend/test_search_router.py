import pytest
from unittest.mock import patch

from services.search_router import INTENT_WORD_THRESHOLD, _is_intent_query, handle_search


# ── _is_intent_query ──────────────────────────────────────────────────────────

def test_single_word_is_direct():
    assert not _is_intent_query("Gladiator")


def test_two_words_is_direct():
    assert not _is_intent_query("Dark Knight")


def test_exactly_threshold_words_is_direct():
    query = " ".join(["word"] * INTENT_WORD_THRESHOLD)
    assert not _is_intent_query(query)


def test_one_above_threshold_is_intent():
    query = " ".join(["word"] * (INTENT_WORD_THRESHOLD + 1))
    assert _is_intent_query(query)


def test_long_sentence_is_intent():
    assert _is_intent_query("a slow burn psychological thriller like Christopher Nolan")


# ── handle_search ─────────────────────────────────────────────────────────────

def test_handle_search_direct_mode():
    with patch("services.search_router.api_client.search_movies", return_value=[{"id": "1"}]) as mock:
        result = handle_search("Gladiator")
    assert result["mode"] == "direct"
    assert result["query"] == "Gladiator"
    assert result["results"] == [{"id": "1"}]
    mock.assert_called_once_with("Gladiator", mode="direct")


def test_handle_search_intent_mode():
    long_query = "a slow burn psychological thriller like Nolan films"
    with patch("services.search_router.api_client.search_movies", return_value=[{"id": "2"}]) as mock:
        result = handle_search(long_query)
    assert result["mode"] == "intent"
    assert result["results"] == [{"id": "2"}]
    mock.assert_called_once_with(long_query, mode="intent")


def test_handle_search_strips_whitespace():
    with patch("services.search_router.api_client.search_movies", return_value=[]):
        result = handle_search("  Titanic  ")
    assert result["query"] == "Titanic"


def test_handle_search_returns_required_keys():
    with patch("services.search_router.api_client.search_movies", return_value=[]):
        result = handle_search("Jaws")
    assert {"mode", "query", "results"} <= result.keys()
