"""Conexión a MongoDB e índices.

Un único MongoClient por proceso (pymongo ya gestiona un pool de conexiones internamente).
"""

from flask import Flask, current_app
from pymongo import ASCENDING, MongoClient
from pymongo.database import Database


def init_db(app: Flask) -> None:
    client = MongoClient(app.config["MONGO_URI"], serverSelectionTimeoutMS=5000, tz_aware=True)
    database = client.get_default_database()

    app.extensions["mongo_client"] = client
    app.extensions["mongo_db"] = database
    ensure_indexes(database)


def get_db() -> Database:
    return current_app.extensions["mongo_db"]


def ensure_indexes(db: Database) -> None:
    """Crear índices es idempotente: si ya existen, MongoDB no hace nada."""
    db.foods.create_index("key", unique=True)
    db.foods.create_index([("category", ASCENDING), ("name", ASCENDING)])
    db.foods.create_index("name_lower")

    db.users.create_index("email", unique=True, sparse=True)
    db.users.create_index("google_sub", unique=True, sparse=True)
    # TTL: MongoDB borra solo los usuarios invitados cuando pasa su fecha de caducidad
    db.users.create_index("expires_at", expireAfterSeconds=0)

    db.diets.create_index([("user_id", ASCENDING), ("start_date", ASCENDING)])
    db.diets.create_index("expires_at", expireAfterSeconds=0)
