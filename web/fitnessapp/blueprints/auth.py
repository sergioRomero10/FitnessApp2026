"""Inicio de sesión: Google (OpenID Connect con Authlib) y modo invitado.

Cambios respecto a la versión original:
- El client secret ya no está en el código ni en un client_secret.json del repositorio:
  se lee de variables de entorno.
- Ya no se usa OAUTHLIB_INSECURE_TRANSPORT ni `pip._vendor.cachecontrol` (código interno
  de pip). Authlib valida `state`, `nonce` y la firma del id_token.
- Antes había un único objeto `Flow` global compartido por todos los usuarios: dos logins
  simultáneos podían mezclar su `state`. Authlib guarda el estado en la sesión de cada uno.
- Sin el `time.sleep(5)` del callback.

Todas las peticiones POST están protegidas con CSRF de forma global (CSRFProtect).
"""

from authlib.integrations.flask_client import OAuth, OAuthError
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from ..auth import login_user, safe_next
from ..db import get_db
from ..forms import EmptyForm
from ..services import users

bp = Blueprint("auth", __name__)
oauth = OAuth()


def init_oauth(app) -> None:
    oauth.init_app(app)
    if app.config["GOOGLE_CLIENT_ID"]:
        oauth.register(
            name="google",
            client_id=app.config["GOOGLE_CLIENT_ID"],
            client_secret=app.config["GOOGLE_CLIENT_SECRET"],
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )


def _google():
    client = oauth.create_client("google")
    if client is None:  # login con Google no configurado
        abort(404)
    return client


@bp.get("/login")
def login():
    return render_template("auth/login.html", form=EmptyForm(), next=request.args.get("next", ""))


@bp.post("/auth/guest")
def guest():
    if not current_app.config["DEMO_MODE"]:
        abort(404)
    user = users.create_guest(get_db(), current_app.config["GUEST_TTL"])
    login_user(user)
    flash(
        f"Welcome! You are browsing as {user['name']}. Guest data is deleted after a few days.",
        "info",
    )
    return redirect(safe_next(request.form.get("next")))


@bp.get("/auth/google")
def google_login():
    client = _google()
    session["login_next"] = safe_next(request.args.get("next"))
    return client.authorize_redirect(url_for("auth.google_callback", _external=True))


@bp.get("/auth/callback")
def google_callback():
    client = _google()
    next_url = session.pop("login_next", None)
    try:
        token = client.authorize_access_token()
    except OAuthError as exc:
        current_app.logger.warning("Login con Google fallido: %s", exc)
        flash("Google sign-in was cancelled or failed. Please try again.", "danger")
        return redirect(url_for("auth.login"))

    userinfo = token.get("userinfo") or client.userinfo()
    user = users.upsert_google_user(get_db(), userinfo)
    login_user(user)
    flash(f"Welcome, {user['name']}!", "success")
    return redirect(safe_next(next_url))


@bp.post("/logout")
def logout():
    # Antes era GET: cualquier enlace o <img> de otra web podía cerrarte la sesión
    session.clear()
    flash("You have logged out.", "info")
    return redirect(url_for("foods.index"))
