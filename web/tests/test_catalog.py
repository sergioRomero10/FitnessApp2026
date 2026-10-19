from fitnessapp.services import catalog


def test_normalize_row_converts_text_to_numbers():
    doc = catalog.normalize_row(
        {
            "FoodCategory": "Non-AlcoholicDrinks&Beverages",
            "FoodItem": " Coca Cola ",
            "per100grams": "100ml",
            "Cals_per100grams": "42 cal",
            "KJ_per100grams": "176 kJ",
        }
    )
    assert doc == {
        "key": "non-alcoholic-drinks-beverages/coca-cola",
        "name": "Coca Cola",
        "name_lower": "coca cola",
        "category": "Non-Alcoholic Drinks & Beverages",
        "unit": "ml",
        "kcal_per_100": 42.0,
        "kj_per_100": 176.0,
    }


def test_pretty_category_handles_dataset_formats():
    assert catalog.pretty_category("(Fruit)Juices") == "(Fruit) Juices"
    assert catalog.pretty_category("Pastries,Breads&Rolls") == "Pastries, Breads & Rolls"
    assert catalog.pretty_category("Cakes&Pies") == "Cakes & Pies"


def test_same_name_in_two_categories_are_different_foods(db):
    # El original guardaba por nombre y una 'Almonds' sobrescribía a la otra
    assert db.foods.count_documents({"name": "Almonds"}) == 2


def test_upsert_is_idempotent(db, app):
    before = db.foods.count_documents({})
    catalog.upsert_foods(
        db,
        [
            catalog.normalize_row(
                {
                    "FoodCategory": "Fruits",
                    "FoodItem": "Apple",
                    "per100grams": "100g",
                    "Cals_per100grams": "53 cal",
                    "KJ_per100grams": "222 kJ",
                }
            )
        ],
    )
    assert db.foods.count_documents({}) == before
    assert db.foods.find_one({"key": "fruits/apple"})["kcal_per_100"] == 53


def test_real_csv_loads_completely():
    from pathlib import Path

    csv_path = Path(__file__).resolve().parents[2] / "data" / "calories.csv"
    docs = catalog.load_csv(csv_path)
    assert len(docs) == 2224  # 2.225 filas, una repetida
    assert len({d["key"] for d in docs}) == len(docs), "las claves deben ser únicas"
    assert all(d["kcal_per_100"] >= 0 for d in docs)
