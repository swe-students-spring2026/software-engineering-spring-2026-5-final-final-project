"""Frontend route tests — @Karen Maza.

All external HTTP calls are intercepted with the `responses` library so
no real backend is needed during CI.
"""

import json
import sys
import os

import pytest
import responses as rsps_lib

# Allow importing frontend app from this location
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app  # noqa: E402

BACKEND = "http://backend:5000"


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as c:
        yield c


@pytest.fixture()
def auth_client(client):
    """Client with a session token pre-set."""
    with client.session_transaction() as sess:
        sess["token"] = "fake-jwt"
        sess["user_id"] = "abc123"
        sess["username"] = "alice"
    return client


# ------------------------------------------------------------------ root

def test_index_no_session_redirects(client):
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_index_with_session_redirects_dashboard(auth_client):
    resp = auth_client.get("/")
    assert resp.status_code == 302
    assert "/dashboard" in resp.headers["Location"]


# ------------------------------------------------------------------ login

def test_login_page_get(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"Sign In" in resp.data


@rsps_lib.activate
def test_login_post_success(client):
    rsps_lib.add(
        rsps_lib.POST,
        f"{BACKEND}/api/auth/login",
        json={"token": "tok123", "user_id": "u1"},
        status=200,
    )
    resp = client.post("/login", data={"username": "alice", "password": "secret"}, follow_redirects=False)
    assert resp.status_code == 302
    assert "/dashboard" in resp.headers["Location"]
    with client.session_transaction() as sess:
        assert sess["token"] == "tok123"
        assert sess["user_id"] == "u1"
        assert sess["username"] == "alice"



@rsps_lib.activate
def test_login_post_failure(client):
    rsps_lib.add(
        rsps_lib.POST,
        f"{BACKEND}/api/auth/login",
        json={"error": "Invalid credentials"},
        status=401,
    )
    resp = client.post("/login", data={"username": "alice", "password": "wrong"}, follow_redirects=True)
    assert b"Invalid credentials" in resp.data

@rsps_lib.activate
def test_login_post_generic_error_message(client):
    rsps_lib.add(rsps_lib.POST, f"{BACKEND}/api/auth/login", json={}, status=401)
    resp = client.post("/login", data={"username": "alice", "password": "wrong"}, follow_redirects=True)
    assert b"Login failed" in resp.data


def test_login_backend_down(client):
    resp = client.post("/login", data={"username": "alice", "password": "x"}, follow_redirects=True)
    assert b"Cannot reach" in resp.data


# ------------------------------------------------------------------ register

def test_register_page_get(client):
    resp = client.get("/register")
    assert resp.status_code == 200
    assert b"Create Account" in resp.data


@rsps_lib.activate
def test_register_post_success(client):
    rsps_lib.add(
        rsps_lib.POST,
        f"{BACKEND}/api/auth/register",
        json={"message": "User registered successfully", "user_id": "u1"},
        status=201,
    )
    resp = client.post(
        "/register",
        data={"username": "alice", "password": "secret", "email": "a@b.com"},
        follow_redirects=True,
    )
    assert b"Account created" in resp.data

@rsps_lib.activate
def test_register_post_generic_error_message(client):
    rsps_lib.add(rsps_lib.POST, f"{BACKEND}/api/auth/register", json={}, status=400)
    resp = client.post("/register", data={"username": "x", "password": "y"}, follow_redirects=True)
    assert b"Registration failed" in resp.data


@rsps_lib.activate
def test_register_post_conflict(client):
    rsps_lib.add(
        rsps_lib.POST,
        f"{BACKEND}/api/auth/register",
        json={"error": "Username already exists"},
        status=409,
    )
    resp = client.post(
        "/register",
        data={"username": "alice", "password": "secret"},
        follow_redirects=True,
    )
    assert b"Username already exists" in resp.data


def test_register_backend_down(client):
    resp = client.post("/register", data={"username": "x", "password": "y"}, follow_redirects=True)
    assert b"Cannot reach" in resp.data


# ------------------------------------------------------------------ logout

def test_logout_clears_session(auth_client):
    resp = auth_client.get("/logout", follow_redirects=False)
    assert resp.status_code == 302
    with auth_client.session_transaction() as sess:
        assert "token" not in sess


# ------------------------------------------------------------------ dashboard

def test_dashboard_requires_login(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


@rsps_lib.activate
def test_dashboard_renders(auth_client):
    rsps_lib.add(rsps_lib.GET, f"{BACKEND}/api/analytics/monthly-summary", json={"monthly_summary": []}, status=200)
    rsps_lib.add(rsps_lib.GET, f"{BACKEND}/api/analytics/spending-trends", json={"spending_trends": []}, status=200)
    rsps_lib.add(rsps_lib.GET, f"{BACKEND}/api/analytics/top-categories", json={"top_categories": []}, status=200)
    resp = auth_client.get("/dashboard")
    assert resp.status_code == 200
    assert b"Dashboard" in resp.data


@rsps_lib.activate
def test_dashboard_renders_charts_and_table(auth_client):
    rsps_lib.add(
        rsps_lib.GET,
        f"{BACKEND}/api/analytics/monthly-summary",
        json={"monthly_summary": [{"month": "2026-04", "income": 100.0, "expense": 40.0, "net": 60.0}]},
        status=200,
    )
    rsps_lib.add(
        rsps_lib.GET,
        f"{BACKEND}/api/analytics/spending-trends",
        json={"spending_trends": [{"month": "2026-03", "total_spent": 10.0}, {"month": "2026-04", "total_spent": 20.0}]},
        status=200,
    )
    rsps_lib.add(
        rsps_lib.GET,
        f"{BACKEND}/api/analytics/top-categories",
        json={"top_categories": [{"category": "food", "total_spent": 15.5}]},
        status=200,
    )
    resp = auth_client.get("/dashboard")
    assert resp.status_code == 200
    assert b"2026-04" in resp.data
    assert b"categoryChart" in resp.data
    assert b"trendsChart" in resp.data


def test_dashboard_backend_down(auth_client):
    resp = auth_client.get("/dashboard")
    assert resp.status_code == 200  # renders with empty data gracefully


# ------------------------------------------------------------------ transactions

def test_transactions_requires_login(client):
    resp = client.get("/transactions")
    assert resp.status_code == 302


@rsps_lib.activate
def test_transactions_list(auth_client):
    rsps_lib.add(
        rsps_lib.GET,
        f"{BACKEND}/api/transactions",
        json={"transactions": [{"_id": "abc", "type": "expense", "amount": 10.0, "category": "food", "date": "2026-04-01", "description": "lunch"}]},
        status=200,
    )
    resp = auth_client.get("/transactions")
    assert resp.status_code == 200
    assert b"food" in resp.data


@rsps_lib.activate
def test_transactions_create(auth_client):
    rsps_lib.add(rsps_lib.POST, f"{BACKEND}/api/transactions", json={"message": "Transaction created successfully", "transaction_id": "abc"}, status=201)
    rsps_lib.add(rsps_lib.GET, f"{BACKEND}/api/transactions", json={"transactions": []}, status=200)
    resp = auth_client.post(
        "/transactions",
        data={"type": "expense", "amount": "10.00", "category": "food", "date": "2026-04-01", "description": ""},
        follow_redirects=True,
    )
    assert b"Transaction added" in resp.data


@rsps_lib.activate
def test_transactions_create_failure(auth_client):
    rsps_lib.add(rsps_lib.POST, f"{BACKEND}/api/transactions", json={"error": "Bad input"}, status=400)
    rsps_lib.add(rsps_lib.GET, f"{BACKEND}/api/transactions", json={"transactions": []}, status=200)
    resp = auth_client.post(
        "/transactions",
        data={"type": "expense", "amount": "10.00", "category": "food", "date": "2026-04-01"},
        follow_redirects=True,
    )
    assert b"Bad input" in resp.data


@rsps_lib.activate
def test_delete_transaction(auth_client):
    rsps_lib.add(rsps_lib.DELETE, f"{BACKEND}/api/transactions/abc", json={"message": "ok"}, status=200)
    rsps_lib.add(rsps_lib.GET, f"{BACKEND}/api/transactions", json={"transactions": []}, status=200)
    resp = auth_client.post("/transactions/abc/delete", follow_redirects=False)
    assert resp.status_code == 302


def test_delete_transaction_backend_unreachable_flashes(auth_client):
    resp = auth_client.post("/transactions/xyz/delete", follow_redirects=True)
    assert b"Cannot reach" in resp.data


@rsps_lib.activate
def test_transactions_create_generic_error_message(auth_client):
    rsps_lib.add(rsps_lib.POST, f"{BACKEND}/api/transactions", json={}, status=400)
    rsps_lib.add(rsps_lib.GET, f"{BACKEND}/api/transactions", json={"transactions": []}, status=200)
    resp = auth_client.post(
        "/transactions",
        data={"type": "expense", "amount": "1", "category": "x", "date": "2026-04-01"},
        follow_redirects=True,
    )
    assert b"Failed to add transaction" in resp.data


def test_transactions_backend_down(auth_client):
    resp = auth_client.get("/transactions")
    assert resp.status_code == 200


# ------------------------------------------------------------------ budgets

def test_budgets_requires_login(client):
    resp = client.get("/budgets")
    assert resp.status_code == 302


@rsps_lib.activate
def test_budgets_list(auth_client):
    rsps_lib.add(
        rsps_lib.GET,
        f"{BACKEND}/api/budgets/status",
        json={"status": [{"budget_id": "b1", "category": "food", "month": "2026-04", "limit": 300.0, "spent": 100.0, "remaining": 200.0, "over_budget": False}]},
        status=200,
    )
    resp = auth_client.get("/budgets")
    assert resp.status_code == 200
    assert b"food" in resp.data


@rsps_lib.activate
def test_budgets_create(auth_client):
    rsps_lib.add(rsps_lib.POST, f"{BACKEND}/api/budgets", json={"message": "Budget created successfully", "budget_id": "b1"}, status=201)
    rsps_lib.add(rsps_lib.GET, f"{BACKEND}/api/budgets/status", json={"status": []}, status=200)
    resp = auth_client.post(
        "/budgets",
        data={"category": "food", "limit": "300.00", "month": "2026-04"},
        follow_redirects=True,
    )
    assert b"Budget created" in resp.data


@rsps_lib.activate
def test_budgets_create_failure(auth_client):
    rsps_lib.add(rsps_lib.POST, f"{BACKEND}/api/budgets", json={"error": "Missing field"}, status=400)
    rsps_lib.add(rsps_lib.GET, f"{BACKEND}/api/budgets/status", json={"status": []}, status=200)
    resp = auth_client.post(
        "/budgets",
        data={"category": "food", "limit": "300.00", "month": "2026-04"},
        follow_redirects=True,
    )
    assert b"Missing field" in resp.data


@rsps_lib.activate
def test_delete_budget(auth_client):
    rsps_lib.add(rsps_lib.DELETE, f"{BACKEND}/api/budgets/b1", json={"message": "ok"}, status=200)
    rsps_lib.add(rsps_lib.GET, f"{BACKEND}/api/budgets/status", json={"status": []}, status=200)
    resp = auth_client.post("/budgets/b1/delete", follow_redirects=False)
    assert resp.status_code == 302


def test_delete_budget_backend_unreachable_flashes(auth_client):
    resp = auth_client.post("/budgets/b99/delete", follow_redirects=True)
    assert b"Cannot reach" in resp.data


@rsps_lib.activate
def test_budgets_create_generic_error_message(auth_client):
    rsps_lib.add(rsps_lib.POST, f"{BACKEND}/api/budgets", json={}, status=400)
    rsps_lib.add(rsps_lib.GET, f"{BACKEND}/api/budgets/status", json={"status": []}, status=200)
    resp = auth_client.post(
        "/budgets",
        data={"category": "food", "limit": "10", "month": "2026-04"},
        follow_redirects=True,
    )
    assert b"Failed to create budget" in resp.data


def test_budgets_backend_down(auth_client):
    resp = auth_client.get("/budgets")
    assert resp.status_code == 200


@rsps_lib.activate
def test_transactions_list_income_row(auth_client):
    rsps_lib.add(
        rsps_lib.GET,
        f"{BACKEND}/api/transactions",
        json={
            "transactions": [
                {"_id": "i1", "type": "income", "amount": 500.0, "category": "salary", "date": "2026-04-01", "description": ""}
            ]
        },
        status=200,
    )
    resp = auth_client.get("/transactions")
    assert resp.status_code == 200
    assert b"salary" in resp.data
    assert b"income" in resp.data


@rsps_lib.activate
def test_budgets_over_budget_card(auth_client):
    rsps_lib.add(
        rsps_lib.GET,
        f"{BACKEND}/api/budgets/status",
        json={
            "status": [
                {
                    "budget_id": "b1",
                    "category": "food",
                    "month": "2026-04",
                    "limit": 100.0,
                    "spent": 150.0,
                    "remaining": -50.0,
                    "over_budget": True,
                }
            ]
        },
        status=200,
    )
    resp = auth_client.get("/budgets")
    assert resp.status_code == 200
    assert b"Over by" in resp.data
