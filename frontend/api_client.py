"""HTTP client for the PennyWise backend API (used by Flask routes)."""

from __future__ import annotations

import os
from typing import Any

import requests


def default_base_url() -> str:
    return os.getenv("BACKEND_URL", "http://backend:5000").rstrip("/")


class BackendClient:
    """Thin wrapper around ``requests`` for backend JSON endpoints."""

    def __init__(self, base_url: str | None = None, timeout: float = 5.0) -> None:
        self.base_url = (base_url or default_base_url()).rstrip("/")
        self.timeout = timeout

    def _bearer(self, token: str | None) -> dict[str, str]:
        return {"Authorization": f"Bearer {token or ''}"}

    def login(self, username: str, password: str) -> requests.Response:
        return requests.post(
            f"{self.base_url}/api/auth/login",
            json={"username": username, "password": password},
            timeout=self.timeout,
        )

    def register(self, username: str, password: str, email: str = "") -> requests.Response:
        return requests.post(
            f"{self.base_url}/api/auth/register",
            json={"username": username, "password": password, "email": email},
            timeout=self.timeout,
        )

    def fetch_dashboard_series(self, token: str) -> tuple[list[Any], list[Any], list[Any]]:
        headers = self._bearer(token)
        summary = requests.get(
            f"{self.base_url}/api/analytics/monthly-summary",
            headers=headers,
            timeout=self.timeout,
        )
        trends = requests.get(
            f"{self.base_url}/api/analytics/spending-trends",
            headers=headers,
            timeout=self.timeout,
        )
        categories = requests.get(
            f"{self.base_url}/api/analytics/top-categories",
            headers=headers,
            timeout=self.timeout,
        )
        return (
            summary.json().get("monthly_summary", []),
            trends.json().get("spending_trends", []),
            categories.json().get("top_categories", []),
        )

    def list_transactions(self, token: str) -> requests.Response:
        return requests.get(
            f"{self.base_url}/api/transactions",
            headers=self._bearer(token),
            timeout=self.timeout,
        )

    def create_transaction(self, token: str, payload: dict[str, Any]) -> requests.Response:
        return requests.post(
            f"{self.base_url}/api/transactions",
            json=payload,
            headers=self._bearer(token),
            timeout=self.timeout,
        )

    def delete_transaction(self, token: str, transaction_id: str) -> requests.Response:
        return requests.delete(
            f"{self.base_url}/api/transactions/{transaction_id}",
            headers=self._bearer(token),
            timeout=self.timeout,
        )

    def list_budget_status(self, token: str) -> requests.Response:
        return requests.get(
            f"{self.base_url}/api/budgets/status",
            headers=self._bearer(token),
            timeout=self.timeout,
        )

    def create_budget(self, token: str, payload: dict[str, Any]) -> requests.Response:
        return requests.post(
            f"{self.base_url}/api/budgets",
            json=payload,
            headers=self._bearer(token),
            timeout=self.timeout,
        )

    def delete_budget(self, token: str, budget_id: str) -> requests.Response:
        return requests.delete(
            f"{self.base_url}/api/budgets/{budget_id}",
            headers=self._bearer(token),
            timeout=self.timeout,
        )
