"""Main Flask application for the PennyWise backend API."""

from flask import Flask

from backend.analytics import analytics_bp
from backend.transactions import transactions_bp


def create_app():
    """
    Create and configure the Flask app.
    """
    flask_app = Flask(__name__)

    flask_app.register_blueprint(transactions_bp, url_prefix="/api/transactions")
    flask_app.register_blueprint(analytics_bp, url_prefix="/api/analytics")

    @flask_app.route("/health", methods=["GET"])
    def health():
        return {"status": "ok"}

    return flask_app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
    