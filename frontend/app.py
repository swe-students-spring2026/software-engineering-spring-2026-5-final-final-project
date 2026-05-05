from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def dashboard():
    return render_template("dashboard.html", active_tab="dashboard")

@app.route("/friends")
def friends():
    return render_template("friends.html", active_tab="friends")

@app.route("/add")
def add_expense():
    return render_template("add_expense.html", active_tab="add")

@app.route("/history")
def history():
    return render_template("history.html", active_tab="history")

@app.route("/profile")
def profile():
    return render_template("profile.html", active_tab="profile")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
