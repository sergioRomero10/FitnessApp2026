"""Usuario actual y decorador login_required."""

from functools import wraps
from urllib.parse import urlsplit

from flask import flash, g, redirect, request, session, url_for

from .db import get_db
from .services import users


def load_current_user() -> None:
    user_id = session.get("user_id")
    g.user = users.get(get_db(), user_id) if user_id else None
    if user_id and g.user is None:  # p. ej. invitado ya caducado
        session.clear()


def login_user(user: dict) -> None:
    session.clear()  # evita fijación de sesión
    session["user_id"] = str(user["_id"])
    session.permanent = True


def safe_next(target: str | None, fallback: str = "foods.index") -> str:
    """Devuelve una ruta de esta misma web a la que redirigir (evita redirecciones abiertas).

    Acepta rutas ('/diets') y URLs completas del propio dominio (como el Referer).
    """
    if target:
        parts = urlsplit(target)
        same_site = not parts.netloc or parts.netloc == request.host
        if same_site and parts.path.startswith("/") and not parts.path.startswith("//"):
            return parts.path + (f"?{parts.query}" if parts.query else "")
    return url_for(fallback)


def login_required(view):
    # functools.wraps conserva el nombre de la vista. Sin él, todas las vistas decoradas se
    # llamaban "wrapper" y Flask fallaba al registrar la segunda ruta protegida. Además ahora
    # se pasan *args/**kwargs (antes se llamaba a function() sin argumentos).
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.get("user") is None:
            flash("Log in to use this feature.", "warning")
            return redirect(url_for("auth.login", next=request.full_path))
        return view(*args, **kwargs)

    return wrapped
