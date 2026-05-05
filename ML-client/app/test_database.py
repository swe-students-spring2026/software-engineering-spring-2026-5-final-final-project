"""
Tests for database.py — covers save_session, save_feedback, get_session.
"""
import pytest
from unittest.mock import MagicMock, patch
from bson import ObjectId


# ── save_session ──────────────────────────────────────────────────────────────

def test_save_session_returns_string_id():
    """save_session should return a string session ID on success."""
    fake_id = ObjectId()
    mock_result = MagicMock()
    mock_result.inserted_id = fake_id

    with patch("database.sessions_col") as mock_col:
        mock_col.insert_one.return_value = mock_result
        from database import save_session
        session_id = save_session(
            user_id="user_1",
            mood="happy",
            weather={"temp": 20, "condition": "clear"},
            profile={"valence": 0.8},
            tracks=[{"uri": "spotify:track:abc"}],
        )

    assert isinstance(session_id, str)
    assert session_id == str(fake_id)


def test_save_session_with_none_user_id():
    """save_session should work even when user_id is None."""
    fake_id = ObjectId()
    mock_result = MagicMock()
    mock_result.inserted_id = fake_id

    with patch("database.sessions_col") as mock_col:
        mock_col.insert_one.return_value = mock_result
        from database import save_session
        session_id = save_session(
            user_id=None,
            mood="chill",
            weather={},
            profile={},
            tracks=[],
        )

    assert isinstance(session_id, str)


# ── save_feedback ─────────────────────────────────────────────────────────────

def test_save_feedback_returns_true_on_success():
    """save_feedback should return True when write is acknowledged."""
    mock_result = MagicMock()
    mock_result.acknowledged = True

    with patch("database.feedback_col") as mock_col:
        mock_col.insert_one.return_value = mock_result
        from database import save_feedback
        result = save_feedback("session_abc", "spotify:track:xyz", 5)

    assert result is True


def test_save_feedback_returns_false_when_unacknowledged():
    """save_feedback should return False when write is not acknowledged."""
    mock_result = MagicMock()
    mock_result.acknowledged = False

    with patch("database.feedback_col") as mock_col:
        mock_col.insert_one.return_value = mock_result
        from database import save_feedback
        result = save_feedback("session_abc", "spotify:track:xyz", 3)

    assert result is False


# ── get_session ───────────────────────────────────────────────────────────────

def test_get_session_returns_document():
    """get_session should return a document when found."""
    fake_id = ObjectId()
    expected_doc = {"_id": fake_id, "mood": "happy"}

    with patch("database.sessions_col") as mock_col:
        mock_col.find_one.return_value = expected_doc
        from database import get_session
        result = get_session(str(fake_id))

    assert result == expected_doc


def test_get_session_returns_none_for_invalid_id():
    """get_session should return None for invalid ObjectId strings."""
    from database import get_session
    result = get_session("not-a-valid-object-id")
    assert result is None


def test_get_session_returns_none_when_not_found():
    """get_session should return None when no document matches."""
    with patch("database.sessions_col") as mock_col:
        mock_col.find_one.return_value = None
        from database import get_session
        result = get_session(str(ObjectId()))

    assert result is None
