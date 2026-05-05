import os
from functools import wraps

import requests
from flask import Flask, render_template, session, redirect, url_for, request, flash

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

API_URL = os.environ.get("API_URL", "http://localhost:5001")


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/")
def dashboard():
    username = session["user"]["username"]
    
    friendships_res = requests.get(f"{API_URL}/api/friendships", params={"username": username})
    friendships = friendships_res.json().get("friendships", []) if friendships_res.ok else []
    
    expenses_res = requests.get(f"{API_URL}/api/expenses", params={"username": username})
    expenses = expenses_res.json().get("expenses", []) if expenses_res.ok else []

    # Calculate balance per friend
    balances = {}
    for f in friendships:
        balances[f["friend_username"]] = 0.0

    for expense in expenses:
        payer = expense["payer_username"]
        debtor = expense["debtor_username"]
        amount = expense["amount_owed"]
        if payer == username:
            balances[debtor] = balances.get(debtor, 0) + amount
        elif debtor == username:
            balances[payer] = balances.get(payer, 0) - amount

    total_balance = sum(balances.values())

    print("FRIENDSHIPS:", friendships)
    print("EXPENSES:", expenses)
    print("BALANCES:", balances)

    return render_template("dashboard.html", active_tab="dashboard", friendships=friendships, balances=balances, total_balance=total_balance)

@app.route("/friends")
def friends():
    res = requests.get(f"{API_URL}/api/friendships", params={"username": session["user"]["username"]})
    friendships = res.json().get("friendships", []) if res.ok else []
    return render_template("friends.html", active_tab="friends", friendships=friendships)


@app.route("/add")
def add_expense():
    res = requests.get(f"{API_URL}/api/friendships", params={"username": session["user"]["username"]})
    friendships = res.json().get("friendships", []) if res.ok else []
    return render_template("add_expense.html", active_tab="add", friendships=friendships)

@app.route("/add", methods=["POST"])
def add_expense_post():
    debtor_username = request.form.get("debtor_username", "").strip()
    description = request.form.get("description", "").strip()
    total_amount = request.form.get("total_amount", "").strip()
    amount_owed = request.form.get("amount_owed", "").strip()
    category = request.form.get("category", "general").strip()

    res = requests.post(f"{API_URL}/api/expenses", json={
        "payer_username": session["user"]["username"],
        "debtor_username": debtor_username,
        "description": description,
        "total_amount": float(total_amount),
        "amount_owed": float(amount_owed),
        "category": category,
    })

    if res.ok:
        return redirect("/")
    else:
        friendships_res = requests.get(f"{API_URL}/api/friendships", params={"username": session["user"]["username"]})
        friendships = friendships_res.json().get("friendships", []) if friendships_res.ok else []
        error = res.json().get("error", "Something went wrong.")
        return render_template("add_expense.html", active_tab="add", friendships=friendships, error=error)

@app.route("/history")
@login_required
def history():
    return render_template("history.html", active_tab="history")


@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html", active_tab="profile")


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        try:
            resp = requests.post(
                f"{API_URL}/api/login",
                json={"username": username, "password": password},
                timeout=5,
            )
            if resp.status_code == 200:
                session["user"] = resp.json()
                return redirect(url_for("dashboard"))
            flash(resp.json().get("error", "Invalid credentials"))
        except requests.exceptions.RequestException:
            flash("Could not connect to server")
        return redirect(url_for("login"))
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        email = request.form.get("email", "").strip() or None
        try:
            resp = requests.post(
                f"{API_URL}/api/users",
                json={"username": username, "password": password, "email": email},
                timeout=5,
            )
            if resp.status_code == 201:
                session["user"] = resp.json()
                return redirect(url_for("dashboard"))
            flash(resp.json().get("error", "Registration failed"))
        except requests.exceptions.RequestException:
            flash("Could not connect to server")
        return redirect(url_for("register"))
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/friends/add", methods=["GET"])
def add_friend():
    return render_template("add_friend.html", active_tab="friends")

@app.route("/friends/add", methods=["POST"])
def add_friend_post():
    friend_username = request.form.get("friend_username", "").strip()
    res = requests.post(f"{API_URL}/api/friendships", json={
        "username": session["user"]["username"],
        "friend_username": friend_username
    })
    if res.ok:
        return render_template("add_friend.html", active_tab="friends", success=f"Friend request sent to {friend_username}!")
    else:
        error = res.json().get("error", "Oops! Something went wrong.")
        return render_template("add_friend.html", active_tab="friends", error=error)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
