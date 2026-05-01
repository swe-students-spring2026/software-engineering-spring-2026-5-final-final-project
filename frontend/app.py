"""PennyWise frontend — Flask app that renders templates and proxies to backend API."""

import os
from functools import wraps
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, url_for

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:5000")


def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("FLASK_SECRET", "dev-frontend-secret")

    def login_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "token" not in session:
                return redirect(url_for("login"))
            return f(*args, **kwargs)
        return decorated

    def _headers():
        return {"Authorization": f"Bearer {session.get('token', '')}"}

    # ------------------------------------------------------------------ auth

    @app.route("/")
    def index():
        if "token" in session:
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            payload = {"username": request.form["username"], "password": request.form["password"]}
            try:
                resp = requests.post(f"{BACKEND_URL}/api/auth/login", json=payload, timeout=5)
            except requests.exceptions.RequestException:
                flash("Cannot reach backend service.", "danger")
                return render_template("login.html")

            if resp.status_code == 200:
                data = resp.json()
                session["token"] = data["token"]
                session["user_id"] = data["user_id"]
                session["username"] = request.form["username"]
                return redirect(url_for("dashboard"))

            flash(resp.json().get("error", "Login failed"), "danger")
        return render_template("login.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            payload = {
                "username": request.form["username"],
                "password": request.form["password"],
                "email": request.form.get("email", ""),
            }
            try:
                resp = requests.post(f"{BACKEND_URL}/api/auth/register", json=payload, timeout=5)
            except requests.exceptions.RequestException:
                flash("Cannot reach backend service.", "danger")
                return render_template("register.html")

            if resp.status_code == 201:
                flash("Account created! Please log in.", "success")
                return redirect(url_for("login"))

            flash(resp.json().get("error", "Registration failed"), "danger")
        return render_template("register.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    # ------------------------------------------------------------------ dashboard

    @app.route("/dashboard")
    @login_required
    def dashboard():
        try:
            summary_resp = requests.get(f"{BACKEND_URL}/api/analytics/monthly-summary", headers=_headers(), timeout=5)
            trends_resp = requests.get(f"{BACKEND_URL}/api/analytics/spending-trends", headers=_headers(), timeout=5)
            cats_resp = requests.get(f"{BACKEND_URL}/api/analytics/top-categories", headers=_headers(), timeout=5)
            monthly = summary_resp.json().get("monthly_summary", [])
            trends = trends_resp.json().get("spending_trends", [])
            categories = cats_resp.json().get("top_categories", [])
        except requests.exceptions.RequestException:
            monthly, trends, categories = [], [], []

        return render_template("dashboard.html", monthly=monthly, trends=trends, categories=categories)

    # ------------------------------------------------------------------ transactions

    @app.route("/transactions", methods=["GET", "POST"])
    @login_required
    def transactions():
        if request.method == "POST":
            payload = {
                "type": request.form["type"],
                "amount": float(request.form["amount"]),
                "category": request.form["category"],
                "description": request.form.get("description", ""),
                "date": request.form["date"],
            }
            try:
                resp = requests.post(f"{BACKEND_URL}/api/transactions", json=payload, headers=_headers(), timeout=5)
                if resp.status_code == 201:
                    flash("Transaction added.", "success")
                else:
                    flash(resp.json().get("error", "Failed to add transaction"), "danger")
            except requests.exceptions.RequestException:
                flash("Cannot reach backend service.", "danger")
            return redirect(url_for("transactions"))

        try:
            resp = requests.get(f"{BACKEND_URL}/api/transactions", headers=_headers(), timeout=5)
            items = resp.json().get("transactions", [])
        except requests.exceptions.RequestException:
            items = []

        return render_template("transactions.html", transactions=items)

    @app.route("/transactions/<tid>/delete", methods=["POST"])
    @login_required
    def delete_transaction(tid):
        try:
            requests.delete(f"{BACKEND_URL}/api/transactions/{tid}", headers=_headers(), timeout=5)
        except requests.exceptions.RequestException:
            flash("Cannot reach backend service.", "danger")
        return redirect(url_for("transactions"))

    # ------------------------------------------------------------------ budgets

    @app.route("/budgets", methods=["GET", "POST"])
    @login_required
    def budgets():
        if request.method == "POST":
            payload = {
                "category": request.form["category"],
                "limit": float(request.form["limit"]),
                "month": request.form["month"],
            }
            try:
                resp = requests.post(f"{BACKEND_URL}/api/budgets", json=payload, headers=_headers(), timeout=5)
                if resp.status_code == 201:
                    flash("Budget created.", "success")
                else:
                    flash(resp.json().get("error", "Failed to create budget"), "danger")
            except requests.exceptions.RequestException:
                flash("Cannot reach backend service.", "danger")
            return redirect(url_for("budgets"))

        try:
            status_resp = requests.get(f"{BACKEND_URL}/api/budgets/status", headers=_headers(), timeout=5)
            status = status_resp.json().get("status", [])
        except requests.exceptions.RequestException:
            status = []

        return render_template("budgets.html", budgets=status)

    @app.route("/budgets/<bid>/delete", methods=["POST"])
    @login_required
    def delete_budget(bid):
        try:
            requests.delete(f"{BACKEND_URL}/api/budgets/{bid}", headers=_headers(), timeout=5)
        except requests.exceptions.RequestException:
            flash("Cannot reach backend service.", "danger")
        return redirect(url_for("budgets"))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
