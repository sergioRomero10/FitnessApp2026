"""Consultas sobre el catálogo de alimentos."""

import math
import re
from dataclasses import dataclass

from pymongo.database import Database


@dataclass
class Page:
    items: list[dict]
    page: int
    per_page: int
    total: int

    @property
    def pages(self) -> int:
        return max(1, math.ceil(self.total / self.per_page))


def search(
    db: Database, q: str = "", category: str = "", page: int = 1, per_page: int = 25
) -> Page:
    """Búsqueda y paginación en el servidor.

    Antes se mandaban los ~2.200 alimentos en cada visita y DataTables filtraba en el navegador.
    """
    query: dict = {}
    if q:
        # re.escape evita que lo que escribe el usuario se interprete como expresión regular
        query["name_lower"] = {"$regex": re.escape(q.strip().lower())}
    if category:
        query["category"] = category

    total = db.foods.count_documents(query)
    page = max(1, min(page, max(1, math.ceil(total / per_page))))
    cursor = (
        db.foods.find(query, {"_id": 0})
        .sort([("category", 1), ("name", 1)])
        .skip((page - 1) * per_page)
        .limit(per_page)
    )
    return Page(list(cursor), page, per_page, total)


def categories(db: Database) -> list[str]:
    return sorted(db.foods.distinct("category"))


def by_keys(db: Database, keys: list[str]) -> dict[str, dict]:
    if not keys:
        return {}
    return {f["key"]: f for f in db.foods.find({"key": {"$in": list(keys)}}, {"_id": 0})}


def exists(db: Database, key: str) -> bool:
    return db.foods.count_documents({"key": key}, limit=1) > 0


def count(db: Database) -> int:
    return db.foods.estimated_document_count()
