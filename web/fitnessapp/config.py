"""Configuración leída de variables de entorno (nunca de valores escritos en el código)."""

import os
from datetime import timedelta


def _bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/fitnessapp")

    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

    # Botón "Entrar como invitado": permite probar la app sin cuenta de Google
    DEMO_MODE = _bool("DEMO_MODE", True)
    GUEST_TTL = timedelta(days=int(os.environ.get("GUEST_TTL_DAYS", "7")))

    # Si la colección de alimentos está vacía al arrancar, se carga desde el CSV.
    # Útil cuando se despliega sin Kafka (p. ej. Render + MongoDB Atlas).
    SEED_ON_START = _bool("SEED_ON_START", False)
    CATALOG_CSV = os.environ.get("CATALOG_CSV", "/app/data/calories.csv")

    NOMINATIM_URL = os.environ.get("NOMINATIM_URL", "https://nominatim.openstreetmap.org/search")
    NOMINATIM_USER_AGENT = os.environ.get(
        "NOMINATIM_USER_AGENT", "FitnessApp/2.0 (+https://github.com/sergioRomero10)"
    )

    # Cookies de sesión seguras. En local (http) se desactiva Secure con SESSION_COOKIE_SECURE=false
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", True)
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # Número de proxies delante de la app (Render, Caddy, Nginx...) para generar URLs https
    PROXY_COUNT = int(os.environ.get("PROXY_COUNT", "1"))

    FOODS_PER_PAGE = 25
