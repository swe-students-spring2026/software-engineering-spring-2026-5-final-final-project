from flask import Flask
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.movies import movies_bp
from routes.favorites import favorites_bp

app = Flask(__name__)
app.secret_key = "placeholder-secret-key"

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(movies_bp)
app.register_blueprint(favorites_bp)

if __name__ == "__main__":
    app.run(debug=True)
