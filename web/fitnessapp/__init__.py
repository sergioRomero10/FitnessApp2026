"""FitnessApp 2.0 — app factory.

`create_app()` construye la aplicación. Así los tests pueden crear una app con otra
configuración (base de datos en memoria, CSRF desactivado...) sin tocar variables globales.
"""

import logging

import click
from flask import Flask, g, render_template
from flask_wtf.csrf import CSRFError, CSRFProtect
from pymongo.errors import BulkWriteError
from werkzeug.middleware.proxy_fix import ProxyFix

from .auth import load_current_user
from .config import Config
from .db import get_db, init_db
from .forms import EmptyForm
from .services import catalog

csrf = CSRFProtect()


def create_app(overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY no está definida. Copia .env.example a .env y rellénala.")

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    if app.config["PROXY_COUNT"]:
        # Detrás de Render/Caddy/Nginx: respeta X-Forwarded-Proto para generar URLs https
        n = app.config["PROXY_COUNT"]
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=n, x_proto=n, x_host=n)

    csrf.init_app(app)
    init_db(app)

    from .blueprints.auth import bp as auth_bp
    from .blueprints.auth import init_oauth
    from .blueprints.diets import bp as diets_bp
    from .blueprints.favorites import bp as favorites_bp
    from .blueprints.foods import bp as foods_bp
    from .blueprints.gyms import bp as gyms_bp
    from .blueprints.main import bp as main_bp

    init_oauth(app)
    for bp in (main_bp, auth_bp, foods_bp, favorites_bp, diets_bp, gyms_bp):
        app.register_blueprint(bp)

    app.before_request(load_current_user)

    @app.context_processor
    def inject_globals():
        return {
            "current_user": g.get("user"),
            "logout_form": EmptyForm(),
            "google_enabled": bool(app.config["GOOGLE_CLIENT_ID"]),
            "demo_mode": app.config["DEMO_MODE"],
        }

    _register_error_handlers(app)
    _register_cli(app)

    if app.config["SEED_ON_START"]:
        with app.app_context():
            try:
                inserted = catalog.seed_if_empty(get_db(), app.config["CATALOG_CSV"])
            except BulkWriteError:
                # Con varios workers de Gunicorn dos pueden cargar a la vez; el índice único
                # sobre `key` impide duplicados y el otro worker ya habrá completado la carga.
                inserted = 0
            if inserted:
                app.logger.info("Catálogo cargado desde CSV: %s alimentos", inserted)

    return app


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def not_found(_e):
        return render_template("errors/error.html", code=404, title="Page not found"), 404

    @app.errorhandler(CSRFError)
    def csrf_error(_e):
        return render_template(
            "errors/error.html", code=400, title="The form expired. Reload the page and try again."
        ), 400

    @app.errorhandler(500)
    def server_error(_e):
        return render_template("errors/error.html", code=500, title="Something went wrong"), 500


def _register_cli(app: Flask) -> None:
    @app.cli.command("seed")
    @click.option("--csv", "csv_path", default=None, help="Ruta al CSV (por defecto CATALOG_CSV)")
    def seed(csv_path):
        """Carga/actualiza el catálogo de alimentos directamente desde el CSV (sin Kafka)."""
        path = csv_path or app.config["CATALOG_CSV"]
        changed = catalog.upsert_foods(get_db(), catalog.load_csv(path))
        click.echo(f"{changed} alimentos insertados o actualizados desde {path}")
