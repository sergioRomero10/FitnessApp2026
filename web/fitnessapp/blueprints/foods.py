from flask import Blueprint, current_app, g, render_template, request

from ..db import get_db
from ..forms import FoodKeyForm
from ..services import foods

bp = Blueprint("foods", __name__)


@bp.get("/")
def index():
    q = request.args.get("q", "").strip()[:80]
    category = request.args.get("category", "").strip()
    page = request.args.get("page", 1, type=int)

    db = get_db()
    result = foods.search(db, q, category, page, current_app.config["FOODS_PER_PAGE"])
    favorites = set(g.user.get("favorites", [])) if g.user else set()
    return render_template(
        "foods/index.html",
        result=result,
        q=q,
        category=category,
        categories=foods.categories(db),
        favorites=favorites,
        fav_form=FoodKeyForm(),
    )
