from flask import Blueprint, jsonify, render_template

from ..db import get_db
from ..services import foods

bp = Blueprint("main", __name__)


@bp.get("/about")
def about():
    return render_template("about.html", food_count=foods.count(get_db()))


@bp.get("/healthz")
def healthz():
    """Comprobación de salud para Docker y para la plataforma de despliegue."""
    get_db().command("ping")
    return jsonify(status="ok")
