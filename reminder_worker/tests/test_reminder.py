import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from reminder_service import (
    find_due_reminders,
    calculate_next_reminder,
    process_due_reminders,
)
from email_service import email_is_configured, send_task_reminder, send_email


class TestFindDueReminders:
    def test_returns_due_tasks(self):
        mock_collection = MagicMock()
        mock_collection.find.return_value = [{"title": "Task 1"}]
        result = find_due_reminders(mock_collection)
        assert result == [{"title": "Task 1"}]

    def test_returns_empty_when_none_due(self):
        mock_collection = MagicMock()
        mock_collection.find.return_value = []
        result = find_due_reminders(mock_collection)
        assert result == []

    def test_queries_correct_fields(self):
        mock_collection = MagicMock()
        mock_collection.find.return_value = []
        find_due_reminders(mock_collection)
        call_args = mock_collection.find.call_args[0][0]
        assert "completed" in call_args
        assert "reminder_enabled" in call_args
        assert "next_reminder_at" in call_args


class TestCalculateNextReminder:
    def test_minutes(self):
        task = {"repeat_every": 30, "repeat_unit": "minutes"}
        result = calculate_next_reminder(task)
        expected = datetime.now(timezone.utc) + timedelta(minutes=30)
        assert abs((result - expected).total_seconds()) < 2

    def test_hours(self):
        task = {"repeat_every": 2, "repeat_unit": "hours"}
        result = calculate_next_reminder(task)
        expected = datetime.now(timezone.utc) + timedelta(hours=2)
        assert abs((result - expected).total_seconds()) < 2

    def test_days(self):
        task = {"repeat_every": 1, "repeat_unit": "days"}
        result = calculate_next_reminder(task)
        expected = datetime.now(timezone.utc) + timedelta(days=1)
        assert abs((result - expected).total_seconds()) < 2

    def test_weeks(self):
        task = {"repeat_every": 1, "repeat_unit": "weeks"}
        result = calculate_next_reminder(task)
        expected = datetime.now(timezone.utc) + timedelta(weeks=1)
        assert abs((result - expected).total_seconds()) < 2

    def test_missing_repeat_every_returns_none(self):
        task = {"repeat_unit": "days"}
        assert calculate_next_reminder(task) is None

    def test_missing_repeat_unit_returns_none(self):
        task = {"repeat_every": 1}
        assert calculate_next_reminder(task) is None

    def test_invalid_unit_returns_none(self):
        task = {"repeat_every": 1, "repeat_unit": "months"}
        assert calculate_next_reminder(task) is None


class TestProcessDueReminders:
    def test_returns_count_of_processed(self):
        mock_collection = MagicMock()
        mock_collection.find.return_value = [
            {
                "_id": "1",
                "title": "Task",
                "reminder_repeat": False,
                "user_email": "a@a.com",
                "next_reminder_at": datetime.now(timezone.utc),
            }
        ]
        mock_send = MagicMock()
        result = process_due_reminders(mock_collection, mock_send)
        assert result == 1

    def test_calls_send_for_each_task(self):
        mock_collection = MagicMock()
        mock_collection.find.return_value = [
            {
                "_id": "1",
                "title": "Task A",
                "reminder_repeat": False,
                "user_email": "a@a.com",
                "next_reminder_at": datetime.now(timezone.utc),
            },
            {
                "_id": "2",
                "title": "Task B",
                "reminder_repeat": False,
                "user_email": "b@b.com",
                "next_reminder_at": datetime.now(timezone.utc),
            },
        ]
        mock_send = MagicMock()
        process_due_reminders(mock_collection, mock_send)
        assert mock_send.call_count == 2

    def test_disables_reminder_when_no_repeat(self):
        mock_collection = MagicMock()
        mock_collection.find.return_value = [
            {
                "_id": "1",
                "title": "Task",
                "reminder_repeat": False,
                "user_email": "a@a.com",
                "next_reminder_at": datetime.now(timezone.utc),
            }
        ]
        process_due_reminders(mock_collection, MagicMock())
        update_call = mock_collection.update_one.call_args[0][1]
        assert update_call["$set"]["reminder_enabled"] == False

    def test_updates_next_reminder_when_repeat(self):
        mock_collection = MagicMock()
        mock_collection.find.return_value = [
            {
                "_id": "1",
                "title": "Task",
                "reminder_repeat": True,
                "repeat_every": 1,
                "repeat_unit": "days",
                "user_email": "a@a.com",
                "next_reminder_at": datetime.now(timezone.utc),
            }
        ]
        process_due_reminders(mock_collection, MagicMock())
        update_call = mock_collection.update_one.call_args[0][1]
        assert "next_reminder_at" in update_call["$set"]

    def test_returns_zero_when_no_due_tasks(self):
        mock_collection = MagicMock()
        mock_collection.find.return_value = []
        result = process_due_reminders(mock_collection, MagicMock())
        assert result == 0


class TestEmailIsConfigured:
    def test_returns_false_when_no_env_vars(self):
        with patch("email_service.SMTP_HOST", None), patch(
            "email_service.SMTP_USER", None
        ), patch("email_service.SMTP_PASS", None):
            assert email_is_configured() == False

    def test_returns_true_when_all_set(self):
        with patch("email_service.SMTP_HOST", "smtp.gmail.com"), patch(
            "email_service.SMTP_USER", "user@gmail.com"
        ), patch("email_service.SMTP_PASS", "password"):
            assert email_is_configured() == True

    def test_returns_false_when_partially_set(self):
        with patch("email_service.SMTP_HOST", "smtp.gmail.com"), patch(
            "email_service.SMTP_USER", None
        ), patch("email_service.SMTP_PASS", "password"):
            assert email_is_configured() == False


class TestSendEmail:
    def test_skips_when_not_configured(self):
        with patch("email_service.SMTP_HOST", None), patch(
            "email_service.SMTP_USER", None
        ), patch("email_service.SMTP_PASS", None):
            result = send_email("a@a.com", "Subject", "Body")
            assert result == False

    def test_sends_when_configured(self):
        with patch("email_service.SMTP_HOST", "smtp.gmail.com"), patch(
            "email_service.SMTP_USER", "user@gmail.com"
        ), patch("email_service.SMTP_PASS", "password"), patch(
            "smtplib.SMTP"
        ) as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            result = send_email("a@a.com", "Subject", "Body")
            assert result == True

    def test_returns_false_on_smtp_error(self):
        with patch("email_service.SMTP_HOST", "smtp.gmail.com"), patch(
            "email_service.SMTP_USER", "user@gmail.com"
        ), patch("email_service.SMTP_PASS", "password"), patch(
            "smtplib.SMTP", side_effect=Exception("SMTP error")
        ):
            result = send_email("a@a.com", "Subject", "Body")
            assert result == False


class TestSendTaskReminder:
    def test_calls_send_email_with_correct_args(self):
        with patch("email_service.send_email") as mock_send:
            send_task_reminder("a@a.com", "My Task", "2024-01-01")
            mock_send.assert_called_once_with(
                "a@a.com",
                "Reminder: My Task",
                "Your task 'My Task' is due at 2024-01-01",
            )
