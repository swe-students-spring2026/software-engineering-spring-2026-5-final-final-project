from flask import Blueprint, render_template
from services.api_client import get_favorites

favorites_bp = Blueprint("favorites", __name__)


@favorites_bp.route("/favorites")
def favorites():
    saved = get_favorites()
    return render_template("favorites.html", favorites=saved)
