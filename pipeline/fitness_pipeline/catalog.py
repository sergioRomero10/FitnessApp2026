"""Normalización de una fila del CSV de calorías.

Es la misma lógica que web/fitnessapp/services/catalog.py (la web la usa para cargar el CSV
directamente cuando se despliega sin Kafka). Si cambias una, cambia la otra: los tests de
ambos proyectos comprueban el mismo ejemplo.
"""

import re

_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def _number(value: str) -> float:
    match = _NUMBER.search(value or "")
    return float(match.group().replace(",", ".")) if match else 0.0


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def pretty_category(raw: str) -> str:
    text = re.sub(r"(?<=[a-z)])(?=[A-Z(])", " ", raw.strip())
    text = re.sub(r"\s*&\s*", " & ", text)
    return re.sub(r",(?=\S)", ", ", text)


def normalize_row(row: dict) -> dict:
    category = pretty_category(row["FoodCategory"])
    name = row["FoodItem"].strip()
    unit = (row.get("per100grams") or "100g").strip().lower()
    return {
        "key": f"{_slug(category)}/{_slug(name)}",
        "name": name,
        "name_lower": name.lower(),
        "category": category,
        "unit": "ml" if unit.endswith("ml") else "g",
        "kcal_per_100": round(_number(row["Cals_per100grams"]), 1),
        "kj_per_100": round(_number(row["KJ_per100grams"]), 1),
    }
