import json
import os

import pytest
from pymongo import MongoClient

from fitness_pipeline import catalog
from fitness_pipeline.consumer import write_batch

MONGO_TEST_URI = os.environ.get("MONGO_TEST_URI", "mongodb://localhost:27017/pipeline_test")

ROW = {
    "FoodCategory": "Non-AlcoholicDrinks&Beverages",
    "FoodItem": " Coca Cola ",
    "per100grams": "100ml",
    "Cals_per100grams": "42 cal",
    "KJ_per100grams": "176 kJ",
}


@pytest.fixture
def foods():
    client = MongoClient(MONGO_TEST_URI, serverSelectionTimeoutMS=5000)
    db = client.get_default_database()
    db.foods.drop()
    db.foods.create_index("key", unique=True)
    yield db.foods
    client.drop_database(db.name)
    client.close()


def test_normalize_row_matches_web_version():
    # El mismo ejemplo está en web/tests/test_catalog.py: las dos versiones deben coincidir
    assert catalog.normalize_row(ROW) == {
        "key": "non-alcoholic-drinks-beverages/coca-cola",
        "name": "Coca Cola",
        "name_lower": "coca cola",
        "category": "Non-Alcoholic Drinks & Beverages",
        "unit": "ml",
        "kcal_per_100": 42.0,
        "kj_per_100": 176.0,
    }


def test_consumer_upserts_and_skips_bad_messages(foods):
    messages = [json.dumps(ROW).encode(), b"not json", json.dumps({"FoodItem": "x"}).encode()]

    assert write_batch(foods, messages) == 1
    assert foods.count_documents({}) == 1

    # Volver a recibir el mismo mensaje no duplica el alimento
    write_batch(foods, [json.dumps({**ROW, "Cals_per100grams": "43 cal"}).encode()])
    assert foods.count_documents({}) == 1
    assert foods.find_one()["kcal_per_100"] == 43
