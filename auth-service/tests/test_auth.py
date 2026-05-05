"""Tests for the CatCh auth-service FastAPI app."""

import importlib.util
from datetime import timedelta
from pathlib import Path
import smtplib

from fastapi.testclient import TestClient

MODULE_PATH = Path(__file__).resolve().parents[1] / "app" / "main.py"
spec = importlib.util.spec_from_file_location("auth_service_main", MODULE_PATH)
auth_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auth_main)

client = TestClient(auth_main.app)


def setup_function():
    """Reset in-memory verification codes before each test."""

    auth_main.verification_codes.clear()


def test_health():
    """Health endpoint reports auth-service status."""

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "auth-service"


def test_roles_describe_cat_and_kitten_permissions():
    """Role metadata separates cats from the token economy."""

    response = client.get("/auth/roles")
    assert response.status_code == 200
    roles = response.json()["roles"]
    assert roles["kitten"]["token_system_enabled"] is True
    assert roles["cat"]["token_system_enabled"] is False


def test_email_code_can_be_verified_for_kitten():
    """A generated verification code creates a kitten auth token."""

    email = "kitten@example.com"
    send_response = client.post(
        "/auth/send-verification-email",
        json={"email": email, "username": "Tiny Tuna", "role": "kitten"},
    )
    assert send_response.status_code == 200

    code = auth_main.verification_codes[email]["code"]
    verify_response = client.post(
        "/auth/verify-email",
        json={
            "email": email,
            "code": code,
            "username": "Tiny Tuna",
            "role": "kitten",
        },
    )
    assert verify_response.status_code == 200
    body = verify_response.json()
    assert body["username"] == "Tiny_Tuna"
    assert body["role"] == "kitten"
    assert body["token_system_enabled"] is True

    token_response = client.post(
        "/auth/verify-token",
        json={"token": body["token"]},
    )
    assert token_response.status_code == 200
    assert token_response.json()["valid"] is True


def test_invalid_code_is_rejected():
    """Wrong verification codes return a client error."""

    email = "cat@example.com"
    client.post(
        "/auth/send-verification-email",
        json={"email": email, "username": "Professor Cat", "role": "cat"},
    )

    response = client.post(
        "/auth/verify-email",
        json={
            "email": email,
            "code": "000000",
            "username": "Professor Cat",
            "role": "cat",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid verification code"


def test_missing_code_is_rejected():
    """Verifying before requesting a code returns a client error."""

    response = client.post(
        "/auth/verify-email",
        json={
            "email": "missing@example.com",
            "code": "123456",
            "username": "Missing",
            "role": "kitten",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "No verification code found for this email"


def test_expired_code_is_rejected():
    """Expired verification codes are removed and rejected."""

    email = "old@example.com"
    auth_main.verification_codes[email] = {
        "code": "123456",
        "role": "kitten",
        "username": "Old Kitten",
        "created_at": auth_main.utc_now() - timedelta(minutes=20),
        "expires_at": auth_main.utc_now() - timedelta(minutes=1),
        "attempts": 0,
    }

    response = client.post(
        "/auth/verify-email",
        json={
            "email": email,
            "code": "123456",
            "username": "Old Kitten",
            "role": "kitten",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Verification code has expired"
    assert email not in auth_main.verification_codes


def test_too_many_failed_code_attempts_is_rejected():
    """The auth service rejects codes after five failed attempts."""

    email = "locked@example.com"
    auth_main.verification_codes[email] = {
        "code": "123456",
        "role": "kitten",
        "username": "Locked",
        "created_at": auth_main.utc_now(),
        "expires_at": auth_main.utc_now() + timedelta(minutes=10),
        "attempts": 5,
    }

    response = client.post(
        "/auth/verify-email",
        json={
            "email": email,
            "code": "123456",
            "username": "Locked",
            "role": "kitten",
        },
    )
    assert response.status_code == 429
    assert response.json()["detail"] == "Too many failed attempts"
    assert email not in auth_main.verification_codes


def test_refresh_token_preserves_role():
    """Refreshing a valid token keeps role and permissions."""

    email = "teacher@example.com"
    client.post(
        "/auth/send-verification-email",
        json={"email": email, "username": "Pond Cat", "role": "cat"},
    )
    code = auth_main.verification_codes[email]["code"]
    auth_response = client.post(
        "/auth/verify-email",
        json={
            "email": email,
            "code": code,
            "username": "Pond Cat",
            "role": "cat",
        },
    )

    refresh_response = client.post(
        "/auth/refresh-token",
        json={"token": auth_response.json()["token"]},
    )
    assert refresh_response.status_code == 200
    assert refresh_response.json()["role"] == "cat"
    assert refresh_response.json()["token_system_enabled"] is False


def test_invalid_tokens_are_rejected():
    """Invalid JWTs fail validation and refresh."""

    verify_response = client.post("/auth/verify-token", json={"token": "not-a-token"})
    assert verify_response.status_code == 200
    assert verify_response.json()["valid"] is False

    refresh_response = client.post("/auth/refresh-token", json={"token": "not-a-token"})
    assert refresh_response.status_code == 401


def test_send_verification_email_handles_smtp_errors(monkeypatch):
    """SMTP failures are converted into a False delivery result."""

    class FailingSmtp:
        """Small context manager that fails during SMTP login."""

        def __init__(self, server, port):
            self.server = server
            self.port = port

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def starttls(self):
            """Pretend to start TLS."""

            return None

        def login(self, sender, password):
            """Fail SMTP login."""

            raise smtplib.SMTPException("bad credentials")

    monkeypatch.setattr(auth_main, "SENDER_PASSWORD", "configured")
    monkeypatch.setattr(auth_main.smtplib, "SMTP", FailingSmtp)

    assert (
        auth_main.send_verification_email("kitten@example.com", "123456", "kitten")
        is False
    )
