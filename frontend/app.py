from flask import Flask
from dotenv import load_dotenv
from db import mongo
import os

load_dotenv()

app = Flask(__name__)
app.config["MONGO_URI"] = os.getenv("MONGO_URI")
app.secret_key = "placeholder-secret-key"
mongo.init_app(app)

from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.movies import movies_bp
from routes.favorites import favorites_bp

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(movies_bp)
app.register_blueprint(favorites_bp)

if __name__ == "__main__":
    app.run(debug=True)
