from flask import Blueprint, abort, flash, g, jsonify, redirect, render_template, request, url_for

from ..auth import login_required, safe_next
from ..db import get_db
from ..forms import FoodKeyForm
from ..services import foods, users

bp = Blueprint("favorites", __name__, url_prefix="/favorites")


def _wants_json() -> bool:
    return request.accept_mimetypes.best == "application/json"


@bp.get("/")
@login_required
def index():
    db = get_db()
    catalog = foods.by_keys(db, g.user.get("favorites", []))
    items = sorted(catalog.values(), key=lambda f: (f["category"], f["name"]))
    return render_template(
        "favorites/index.html",
        items=items,
        remove_form=FoodKeyForm(),
    )


@bp.post("/toggle")
def toggle():
    """Marca/desmarca un favorito. Responde JSON si la petición viene del JavaScript
    (la estrella cambia sin recargar) o redirige si viene de un formulario normal."""
    if g.user is None:
        if _wants_json():
            return jsonify(error="login_required", login_url=url_for("auth.login")), 401
        flash("Log in to save favourite foods.", "warning")
        return redirect(url_for("auth.login", next=safe_next(request.referrer)))

    form = FoodKeyForm()
    if not form.validate_on_submit() or not foods.exists(get_db(), form.key.data):
        abort(400)

    is_favorite = users.toggle_favorite(get_db(), g.user, form.key.data)
    if _wants_json():
        return jsonify(favorite=is_favorite)
    flash("Added to favourites." if is_favorite else "Removed from favourites.", "success")
    return redirect(safe_next(request.referrer))


@bp.post("/remove")
@login_required
def remove():
    form = FoodKeyForm()
    if form.validate_on_submit():
        users.remove_favorite(get_db(), g.user["_id"], form.key.data)
        flash("Removed from favourites.", "success")
    return redirect(url_for("favorites.index"))
