"""Consumidor: lee el topic de Kafka y guarda el catálogo en MongoDB.

Cambios respecto al original (Kafka_consumer/main.py):
- Upsert en bloque (bulk_write) en lugar de find_one + insert/replace por cada mensaje.
- El offset se confirma (commit) DESPUÉS de escribir en MongoDB. Antes se usaba
  auto-commit: si el proceso caía entre leer y escribir, ese alimento se perdía.
- Se procesan en lotes y se para limpiamente con SIGTERM (docker compose stop).
- Mensajes mal formados se registran y se saltan, en vez de tumbar el consumidor.
- MongoDB con usuario y contraseña (MONGO_URI), no sin autenticación.
"""

import json
import logging
import os
import signal
import sys
from datetime import UTC, datetime

from confluent_kafka import Consumer, KafkaError
from pymongo import MongoClient, UpdateOne
from pymongo.collection import Collection

from .catalog import normalize_row
from .kafka_utils import BOOTSTRAP, TOPIC, ensure_topic

log = logging.getLogger("consumer")
BATCH_SIZE = 200


def to_operations(raw_values: list[bytes]) -> list[UpdateOne]:
    now = datetime.now(UTC)
    ops = []
    for raw in raw_values:
        try:
            doc = normalize_row(json.loads(raw))
        except (ValueError, KeyError, TypeError) as exc:
            log.warning("Mensaje descartado (%s): %r", exc, raw[:200])
            continue
        ops.append(
            UpdateOne(
                {"key": doc["key"]},
                {"$set": {**doc, "updated_at": now}, "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
        )
    return ops


def write_batch(collection: Collection, raw_values: list[bytes]) -> int:
    ops = to_operations(raw_values)
    if not ops:
        return 0
    result = collection.bulk_write(ops, ordered=False)
    return result.upserted_count + result.modified_count


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    ensure_topic()

    mongo = MongoClient(os.environ["MONGO_URI"], serverSelectionTimeoutMS=10000)
    foods = mongo.get_default_database()["foods"]
    foods.create_index("key", unique=True)

    consumer = Consumer(
        {
            "bootstrap.servers": BOOTSTRAP,
            "group.id": os.environ.get("KAFKA_GROUP_ID", "fitnessapp-catalog"),
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    consumer.subscribe([TOPIC])

    running = True

    def stop(*_):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    log.info("Escuchando %s en %s", TOPIC, BOOTSTRAP)
    try:
        while running:
            messages = consumer.consume(num_messages=BATCH_SIZE, timeout=1.0)
            values = []
            for msg in messages:
                if msg.error():
                    if msg.error().code() != KafkaError._PARTITION_EOF:
                        log.error("Error de Kafka: %s", msg.error())
                    continue
                values.append(msg.value())
            if not values:
                continue
            changed = write_batch(foods, values)
            consumer.commit(asynchronous=False)
            log.info(
                "Lote de %s mensajes procesado (%s documentos cambiados)", len(values), changed
            )
    finally:
        consumer.close()
        mongo.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
