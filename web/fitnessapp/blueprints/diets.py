from datetime import date

from flask import Blueprint, abort, flash, g, jsonify, redirect, render_template, url_for

from ..auth import login_required
from ..db import get_db
from ..forms import AddItemForm, DietForm, EmptyForm, FoodKeyForm
from ..services import diets, foods

bp = Blueprint("diets", __name__, url_prefix="/diets")


def _flash_errors(form) -> None:
    for errors in form.errors.values():
        for error in errors:
            flash(error, "danger")


def _get_or_404(diet_id: str) -> dict:
    diet = diets.get(get_db(), g.user, diet_id)
    if diet is None:  # no existe o es de otro usuario
        abort(404)
    return diet


def _add_item_form() -> AddItemForm:
    """El desplegable se rellena con los favoritos del usuario (como en la versión original)."""
    form = AddItemForm()
    favs = foods.by_keys(get_db(), g.user.get("favorites", []))
    form.food.choices = [
        (f["key"], f"{f['name']} · {f['kcal_per_100']:g} kcal/100{f['unit']}")
        for f in sorted(favs.values(), key=lambda f: f["name"])
    ]
    return form


@bp.get("/")
@login_required
def index():
    db = get_db()
    user_diets = diets.list_for(db, g.user)
    totals = {d["_id"]: diets.total_kcal(diets.lines(db, d)) for d in user_diets}
    return render_template(
        "diets/index.html",
        diets=user_diets,
        totals=totals,
        form=DietForm(),
        delete_form=EmptyForm(),
    )


@bp.post("/")
@login_required
def create():
    form = DietForm()
    if not form.validate_on_submit():
        _flash_errors(form)
        return redirect(url_for("diets.index"))
    diet_id = diets.create(
        get_db(), g.user, form.name.data, form.start_date.data, form.end_date.data
    )
    flash(f"Diet “{form.name.data}” created. Now add some foods.", "success")
    return redirect(url_for("diets.detail", diet_id=diet_id))


@bp.get("/<diet_id>")
@login_required
def detail(diet_id):
    diet = _get_or_404(diet_id)
    lines = diets.lines(get_db(), diet)
    edit_form = DietForm(
        data={
            "name": diet["name"],
            "start_date": date.fromisoformat(diet["start_date"]),
            "end_date": date.fromisoformat(diet["end_date"]),
        }
    )
    return render_template(
        "diets/detail.html",
        diet=diet,
        lines=lines,
        total=diets.total_kcal(lines),
        add_form=_add_item_form(),
        edit_form=edit_form,
        remove_form=FoodKeyForm(),
        delete_form=EmptyForm(),
    )


@bp.post("/<diet_id>/edit")
@login_required
def edit(diet_id):
    _get_or_404(diet_id)
    form = DietForm()
    if form.validate_on_submit():
        diets.update(
            get_db(), g.user, diet_id, form.name.data, form.start_date.data, form.end_date.data
        )
        flash("Diet updated.", "success")
    else:
        _flash_errors(form)
    return redirect(url_for("diets.detail", diet_id=diet_id))


@bp.post("/<diet_id>/delete")
@login_required
def delete(diet_id):
    if diets.delete(get_db(), g.user, diet_id):
        flash("Diet deleted.", "success")
    return redirect(url_for("diets.index"))


@bp.post("/<diet_id>/items")
@login_required
def add_item(diet_id):
    _get_or_404(diet_id)
    form = _add_item_form()
    if form.validate_on_submit():  # SelectField solo acepta valores de la lista (sus favoritos)
        diets.add_item(get_db(), g.user, diet_id, form.food.data, form.grams.data)
        flash("Food added to the diet.", "success")
    else:
        _flash_errors(form)
    return redirect(url_for("diets.detail", diet_id=diet_id))


@bp.post("/<diet_id>/items/remove")
@login_required
def remove_item(diet_id):
    form = FoodKeyForm()
    if form.validate_on_submit() and diets.remove_item(get_db(), g.user, diet_id, form.key.data):
        flash("Food removed from the diet.", "success")
    return redirect(url_for("diets.detail", diet_id=diet_id))


@bp.get("/calendar")
@login_required
def calendar():
    return render_template("diets/calendar.html")


@bp.get("/events.json")
@login_required
def events():
    data = diets.calendar_events(get_db(), g.user)
    for event in data:
        event["url"] = url_for("diets.detail", diet_id=event["id"])
    return jsonify(data)
