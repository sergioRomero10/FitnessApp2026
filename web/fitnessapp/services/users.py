"""Usuarios y favoritos.

Todas las modificaciones son operaciones atómicas de MongoDB ($addToSet, $pull...).
Antes se leía el usuario entero, se modificaba en Python y se reescribía con $set: si
llegaban dos peticiones a la vez, una pisaba los cambios de la otra.
"""

import secrets
from datetime import UTC, datetime, timedelta

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument
from pymongo.database import Database


def _oid(value: str | ObjectId) -> ObjectId | None:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


def get(db: Database, user_id: str) -> dict | None:
    oid = _oid(user_id)
    return db.users.find_one({"_id": oid}) if oid else None


def upsert_google_user(db: Database, userinfo: dict) -> dict:
    """Crea el usuario la primera vez que entra con Google y actualiza nombre/foto las siguientes.

    El _id lo genera MongoDB (antes se calculaba con count()+1, que repetía ids).
    """
    now = datetime.now(UTC)
    return db.users.find_one_and_update(
        {"google_sub": userinfo["sub"]},
        {
            "$set": {
                "email": userinfo.get("email"),
                "name": userinfo.get("name") or userinfo.get("email"),
                "picture": userinfo.get("picture"),
                "last_login": now,
            },
            "$setOnInsert": {"favorites": [], "created_at": now, "is_guest": False},
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )


def create_guest(db: Database, ttl: timedelta) -> dict:
    """Usuario temporal para quien visita la demo desde el portfolio.

    `expires_at` + índice TTL: MongoDB lo borra automáticamente pasado ese tiempo.
    """
    now = datetime.now(UTC)
    user = {
        "name": f"Guest {secrets.token_hex(2).upper()}",
        "picture": None,
        "is_guest": True,
        "favorites": [],
        "created_at": now,
        "expires_at": now + ttl,
    }
    user["_id"] = db.users.insert_one(user).inserted_id
    return user


def add_favorite(db: Database, user_id: ObjectId, food_key: str) -> bool:
    """Devuelve True si se añadió, False si ya estaba."""
    result = db.users.update_one({"_id": user_id}, {"$addToSet": {"favorites": food_key}})
    return result.modified_count == 1


def remove_favorite(db: Database, user_id: ObjectId, food_key: str) -> bool:
    result = db.users.update_one({"_id": user_id}, {"$pull": {"favorites": food_key}})
    return result.modified_count == 1


def toggle_favorite(db: Database, user: dict, food_key: str) -> bool:
    """Devuelve el nuevo estado: True si ahora es favorito."""
    if food_key in user.get("favorites", []):
        remove_favorite(db, user["_id"], food_key)
        return False
    add_favorite(db, user["_id"], food_key)
    return True
