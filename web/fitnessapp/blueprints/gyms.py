from dataclasses import asdict

from flask import Blueprint, current_app, render_template, request

from ..services import gyms

bp = Blueprint("gyms", __name__, url_prefix="/gyms")


@bp.get("/")
def index():
    """La búsqueda es un GET (?city=...): no modifica nada y así el resultado se puede compartir."""
    city = request.args.get("city", "").strip()[:80]
    results, error = [], None
    if city:
        try:
            results = gyms.search(
                city,
                url=current_app.config["NOMINATIM_URL"],
                user_agent=current_app.config["NOMINATIM_USER_AGENT"],
            )
        except gyms.GymSearchError as exc:
            current_app.logger.warning("Nominatim: %s", exc.__cause__)
            error = str(exc)
    return render_template(
        "gyms/index.html",
        city=city,
        gyms=results,
        gyms_json=[asdict(gym) for gym in results],
        error=error,
    )
