"""Dietas: cada dieta es un documento propio en la colección `diets`.

Antes las dietas vivían dentro del usuario como un diccionario cuyas claves eran el nombre
de la dieta. Eso rompía con nombres que contienen '.' o '$', obligaba a reescribir el
usuario completo en cada cambio y guardaba las calorías como texto ('21 cal'), que se
quedaban desfasadas si cambiaba el catálogo. Ahora se guardan solo los gramos y las
calorías se calculan al mostrar la dieta.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.database import Database

from . import foods as foods_service


@dataclass
class DietLine:
    key: str
    name: str
    category: str
    grams: int
    unit: str
    kcal: float


def _oid(value: str) -> ObjectId | None:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


def _owner_filter(user: dict, diet_id: str) -> dict | None:
    """Toda consulta lleva el user_id: un usuario nunca puede ver o tocar dietas ajenas."""
    oid = _oid(diet_id)
    return {"_id": oid, "user_id": user["_id"]} if oid else None


def list_for(db: Database, user: dict) -> list[dict]:
    return list(db.diets.find({"user_id": user["_id"]}).sort("start_date", 1))


def get(db: Database, user: dict, diet_id: str) -> dict | None:
    flt = _owner_filter(user, diet_id)
    return db.diets.find_one(flt) if flt else None


def create(db: Database, user: dict, name: str, start: date, end: date) -> ObjectId:
    now = datetime.now(UTC)
    doc = {
        "user_id": user["_id"],
        "name": name.strip(),
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "items": [],
        "created_at": now,
    }
    if user.get("expires_at"):  # las dietas de un invitado caducan con él
        doc["expires_at"] = user["expires_at"]
    return db.diets.insert_one(doc).inserted_id


def update(db: Database, user: dict, diet_id: str, name: str, start: date, end: date) -> bool:
    flt = _owner_filter(user, diet_id)
    if not flt:
        return False
    result = db.diets.update_one(
        flt,
        {
            "$set": {
                "name": name.strip(),
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            }
        },
    )
    return result.matched_count == 1


def delete(db: Database, user: dict, diet_id: str) -> bool:
    flt = _owner_filter(user, diet_id)
    return bool(flt) and db.diets.delete_one(flt).deleted_count == 1


def add_item(db: Database, user: dict, diet_id: str, food_key: str, grams: int) -> bool:
    """Si el alimento ya está en la dieta suma los gramos; si no, lo añade. Ambas son atómicas."""
    flt = _owner_filter(user, diet_id)
    if not flt:
        return False
    result = db.diets.update_one({**flt, "items.key": food_key}, {"$inc": {"items.$.grams": grams}})
    if result.matched_count:
        return True
    result = db.diets.update_one(
        {**flt, "items.key": {"$ne": food_key}},
        {"$push": {"items": {"key": food_key, "grams": grams}}},
    )
    return result.matched_count == 1


def remove_item(db: Database, user: dict, diet_id: str, food_key: str) -> bool:
    flt = _owner_filter(user, diet_id)
    if not flt:
        return False
    return db.diets.update_one(flt, {"$pull": {"items": {"key": food_key}}}).modified_count == 1


def lines(db: Database, diet: dict) -> list[DietLine]:
    """Une los gramos guardados con el catálogo para calcular las calorías actuales."""
    catalog = foods_service.by_keys(db, [i["key"] for i in diet.get("items", [])])
    result = []
    for item in diet.get("items", []):
        food = catalog.get(item["key"])
        if not food:  # el alimento ya no existe en el catálogo
            continue
        kcal = round(food["kcal_per_100"] * item["grams"] / 100, 1)
        result.append(
            DietLine(item["key"], food["name"], food["category"], item["grams"], food["unit"], kcal)
        )
    return result


def total_kcal(diet_lines: list[DietLine]) -> float:
    return round(sum(line.kcal for line in diet_lines), 1)


def calendar_events(db: Database, user: dict) -> list[dict]:
    """Eventos para FullCalendar. En FullCalendar la fecha `end` es exclusiva, por eso se
    usa `allDay` y se suma un día en el navegador (antes el último día no se pintaba)."""
    events = []
    for diet in list_for(db, user):
        events.append(
            {
                "id": str(diet["_id"]),
                "title": diet["name"],
                "start": diet["start_date"],
                "end": diet["end_date"],
                "allDay": True,
            }
        )
    return events
