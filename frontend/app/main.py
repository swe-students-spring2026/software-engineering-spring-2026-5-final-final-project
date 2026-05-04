from flask import Flask
from . import config
from .routes import bp


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = config.SECRET_KEY
    app.register_blueprint(bp)
    return app


app = create_app()
