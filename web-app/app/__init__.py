"""Flask application module."""

from flask import Flask
from dotenv import load_dotenv


def create_app():
    """Create and configure the Flask app."""

    load_dotenv()

    app = Flask(__name__)

    from .routes import main  # pylint: disable=import-outside-toplevel

    app.register_blueprint(main)

    return app
