"""Unit tests for ``api_client.BackendClient`` using ``responses`` (no real backend)."""

import os
import sys

import pytest
import responses as rsps_lib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api_client import BackendClient, default_base_url  # noqa: E402

BASE = "http://backend:5000"


@pytest.fixture()
def client():
    return BackendClient(base_url=BASE, timeout=3.0)


def test_default_base_url_from_env(monkeypatch):
    monkeypatch.setenv("BACKEND_URL", "http://api.example:9000/")
    assert default_base_url() == "http://api.example:9000"


def test_default_base_url_when_unset(monkeypatch):
    monkeypatch.delenv("BACKEND_URL", raising=False)
    assert default_base_url() == "http://backend:5000"


def test_backend_client_strips_trailing_slash():
    c = BackendClient("http://host:1/")
    assert c.base_url == "http://host:1"


@rsps_lib.activate
def test_login(client):
    rsps_lib.add(rsps_lib.POST, f"{BASE}/api/auth/login", json={"ok": True}, status=200)
    r = client.login("a", "b")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


@rsps_lib.activate
def test_register(client):
    rsps_lib.add(rsps_lib.POST, f"{BASE}/api/auth/register", json={"id": "1"}, status=201)
    r = client.register("u", "p", "e@e.com")
    assert r.status_code == 201


@rsps_lib.activate
def test_fetch_dashboard_series(client):
    rsps_lib.add(
        rsps_lib.GET,
        f"{BASE}/api/analytics/monthly-summary",
        json={"monthly_summary": [{"month": "2026-04", "income": 1, "expense": 2, "net": -1}]},
        status=200,
    )
    rsps_lib.add(
        rsps_lib.GET,
        f"{BASE}/api/analytics/spending-trends",
        json={"spending_trends": [{"month": "2026-04", "total_spent": 50.0}]},
        status=200,
    )
    rsps_lib.add(
        rsps_lib.GET,
        f"{BASE}/api/analytics/top-categories",
        json={"top_categories": [{"category": "food", "total_spent": 25.0}]},
        status=200,
    )
    monthly, trends, cats = client.fetch_dashboard_series("tok")
    assert len(monthly) == 1 and monthly[0]["month"] == "2026-04"
    assert trends[0]["total_spent"] == 50.0
    assert cats[0]["category"] == "food"


@rsps_lib.activate
def test_fetch_dashboard_series_missing_keys_defaults_empty(client):
    rsps_lib.add(rsps_lib.GET, f"{BASE}/api/analytics/monthly-summary", json={}, status=200)
    rsps_lib.add(rsps_lib.GET, f"{BASE}/api/analytics/spending-trends", json={}, status=200)
    rsps_lib.add(rsps_lib.GET, f"{BASE}/api/analytics/top-categories", json={}, status=200)
    m, t, c = client.fetch_dashboard_series("")
    assert m == [] and t == [] and c == []


@rsps_lib.activate
def test_list_transactions(client):
    rsps_lib.add(rsps_lib.GET, f"{BASE}/api/transactions", json={"transactions": [{"_id": "1"}]}, status=200)
    r = client.list_transactions("jwt")
    assert r.json()["transactions"][0]["_id"] == "1"


@rsps_lib.activate
def test_create_transaction(client):
    rsps_lib.add(rsps_lib.POST, f"{BASE}/api/transactions", json={"transaction_id": "x"}, status=201)
    r = client.create_transaction("jwt", {"type": "expense", "amount": 1.0, "category": "c", "date": "2026-04-01"})
    assert r.status_code == 201


@rsps_lib.activate
def test_delete_transaction(client):
    rsps_lib.add(rsps_lib.DELETE, f"{BASE}/api/transactions/abc", json={"message": "ok"}, status=200)
    r = client.delete_transaction("jwt", "abc")
    assert r.status_code == 200


@rsps_lib.activate
def test_list_budget_status(client):
    rsps_lib.add(rsps_lib.GET, f"{BASE}/api/budgets/status", json={"status": []}, status=200)
    r = client.list_budget_status("jwt")
    assert r.json()["status"] == []


@rsps_lib.activate
def test_create_budget(client):
    rsps_lib.add(rsps_lib.POST, f"{BASE}/api/budgets", json={"budget_id": "b"}, status=201)
    r = client.create_budget("jwt", {"category": "food", "limit": 100.0, "month": "2026-04"})
    assert r.status_code == 201


@rsps_lib.activate
def test_delete_budget(client):
    rsps_lib.add(rsps_lib.DELETE, f"{BASE}/api/budgets/b1", json={"message": "ok"}, status=200)
    r = client.delete_budget("jwt", "b1")
    assert r.status_code == 200
