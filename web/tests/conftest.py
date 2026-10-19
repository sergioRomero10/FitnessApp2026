import os

import pytest

from fitnessapp import create_app
from fitnessapp.services import catalog

SAMPLE_ROWS = [
    {
        "FoodCategory": "Fruits",
        "FoodItem": "Apple",
        "per100grams": "100g",
        "Cals_per100grams": "52 cal",
        "KJ_per100grams": "218 kJ",
    },
    {
        "FoodCategory": "Fruits",
        "FoodItem": "Banana",
        "per100grams": "100g",
        "Cals_per100grams": "89 cal",
        "KJ_per100grams": "374 kJ",
    },
    {
        "FoodCategory": "Nuts&Seeds",
        "FoodItem": "Almonds",
        "per100grams": "100g",
        "Cals_per100grams": "575 cal",
        "KJ_per100grams": "2415 kJ",
    },
    {
        "FoodCategory": "BakingIngredients",
        "FoodItem": "Almonds",
        "per100grams": "100g",
        "Cals_per100grams": "579 cal",
        "KJ_per100grams": "2432 kJ",
    },
    {
        "FoodCategory": "(Fruit)Juices",
        "FoodItem": "Apple Juice",
        "per100grams": "100ml",
        "Cals_per100grams": "46 cal",
        "KJ_per100grams": "193 kJ",
    },
]

APPLE = "fruits/apple"
BANANA = "fruits/banana"


# Los tests usan un MongoDB real y desechable (ver servicio "tests" en docker-compose.yml).
# Cada test empieza con la base de datos vacía.
MONGO_TEST_URI = os.environ.get("MONGO_TEST_URI", "mongodb://localhost:27017/fitnessapp_test")

TEST_CONFIG = {
    "TESTING": True,
    "SECRET_KEY": "test",
    "MONGO_URI": MONGO_TEST_URI,
    "WTF_CSRF_ENABLED": False,
    "SESSION_COOKIE_SECURE": False,
    "GOOGLE_CLIENT_ID": "",
    "DEMO_MODE": True,
    "SEED_ON_START": False,
    "PROXY_COUNT": 0,
}


@pytest.fixture
def make_app():
    """Crea apps de test y, al terminar, borra la base de datos y cierra conexiones."""
    apps = []

    def factory(**overrides):
        app = create_app({**TEST_CONFIG, **overrides})
        apps.append(app)
        return app

    yield factory
    for app in apps:
        client = app.extensions["mongo_client"]
        client.drop_database(app.extensions["mongo_db"].name)
        client.close()


@pytest.fixture
def app(make_app):
    app = make_app()
    db = app.extensions["mongo_db"]
    for name in ("foods", "users", "diets"):
        db[name].delete_many({})
    catalog.upsert_foods(db, [catalog.normalize_row(r) for r in SAMPLE_ROWS])
    return app


@pytest.fixture
def db(app):
    return app.extensions["mongo_db"]


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def guest(client):
    """Cliente con sesión iniciada como invitado."""
    response = client.post("/auth/guest")
    assert response.status_code == 302
    return client
