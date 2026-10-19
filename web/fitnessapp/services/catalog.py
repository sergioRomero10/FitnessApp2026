"""Catálogo de alimentos: normalización de las filas del CSV y carga en MongoDB.

La misma normalización existe en pipeline/fitness_pipeline/catalog.py (el consumidor de Kafka).
Si cambias el formato de un documento, cámbialo en los dos sitios: los tests de ambos lo vigilan.
"""

import csv
import re
from datetime import UTC, datetime
from pathlib import Path

from pymongo import UpdateOne
from pymongo.database import Database

_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def _number(value: str) -> float:
    match = _NUMBER.search(value or "")
    return float(match.group().replace(",", ".")) if match else 0.0


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def pretty_category(raw: str) -> str:
    """'Non-AlcoholicDrinks&Beverages' -> 'Non-Alcoholic Drinks & Beverages'."""
    text = re.sub(r"(?<=[a-z)])(?=[A-Z(])", " ", raw.strip())
    text = re.sub(r"\s*&\s*", " & ", text)
    return re.sub(r",(?=\S)", ", ", text)


def normalize_row(row: dict) -> dict:
    """Convierte una fila del CSV en el documento que se guarda en la colección `foods`.

    Antes se guardaba todo como texto ('62 cal') y en minúsculas; ahora las calorías son
    números y cada alimento tiene una clave única (categoría + nombre), porque hay nombres
    repetidos en categorías distintas (p. ej. 'Almonds' en frutos secos y en repostería).
    """
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


def upsert_foods(db: Database, docs: list[dict]) -> int:
    """Inserta o actualiza en bloque (una sola ida y vuelta a MongoDB).

    Devuelve cuántos documentos se insertaron o actualizaron.
    """
    if not docs:
        return 0
    now = datetime.now(UTC)
    ops = [
        UpdateOne(
            {"key": d["key"]},
            {"$set": {**d, "updated_at": now}, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        for d in docs
    ]
    result = db.foods.bulk_write(ops, ordered=False)
    return result.upserted_count + result.modified_count


def load_csv(path: str | Path) -> list[dict]:
    """Lee el CSV quitando filas repetidas (el dataset trae 'Raisin Bran Crunch' dos veces)."""
    with open(path, newline="", encoding="utf-8") as fh:
        docs = {}
        for row in csv.DictReader(fh):
            doc = normalize_row(row)
            docs[doc["key"]] = doc
        return list(docs.values())


def seed_if_empty(db: Database, path: str | Path) -> int:
    if db.foods.estimated_document_count() > 0:
        return 0
    return upsert_foods(db, load_csv(path))
