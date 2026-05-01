from werkzeug.security import generate_password_hash, check_password_hash
from flask import Blueprint, request, redirect, url_for, render_template, flash
from flask_login import UserMixin, login_user, logout_user, login_required

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data.get('_id'))
        self.username = user_data.get('username')
        self.email = user_data.get('email')

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')

        existing_user = auth_bp.db.users.find_one({"username": username})
        if existing_user:
            flash("Username already exists. Please pick another one.")
            return redirect(url_for('auth.register'))
        
        hashed = generate_password_hash(password, method='pbkdf2:sha256')
        
        auth_bp.db.users.insert_one({
            "username": username,
            "password": hashed,
            "email": email
        })
        flash("Registration successful! Please login.")
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_data = auth_bp.db.users.find_one({"username": username})
        if user_data and check_password_hash(user_data['password'], password):
            user_obj = User(user_data)
            login_user(user_obj)
            return redirect(url_for('tasks.show_tasks'))
        flash("Invalid credentials.")
        return redirect(url_for('auth.login'))
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
