"""Productor: publica cada fila del CSV de calorías en Kafka.

Cambios respecto al original (Kafka_producer/main.py):
- confluent-kafka en lugar de kafka-python 2.0.2 (que no funciona en Python 3.12+).
- Cada mensaje lleva como clave el identificador del alimento: así todas las versiones de
  un mismo alimento van a la misma partición y se procesan en orden.
- Callback de entrega: si un mensaje falla se registra y el proceso termina con error
  (antes se capturaba cualquier excepción y se imprimía sin más).
- Logging en vez de print de cada mensaje.
"""

import csv
import json
import logging
import os
import sys

from confluent_kafka import Producer

from .catalog import normalize_row
from .kafka_utils import BOOTSTRAP, TOPIC, ensure_topic

log = logging.getLogger("producer")
CSV_PATH = os.environ.get("CATALOG_CSV", "/app/data/calories.csv")


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    ensure_topic()

    producer = Producer({"bootstrap.servers": BOOTSTRAP, "enable.idempotence": True, "acks": "all"})
    failures = 0

    def on_delivery(err, msg):
        nonlocal failures
        if err is not None:
            failures += 1
            log.error("Error entregando %s: %s", msg.key(), err)

    sent = 0
    with open(CSV_PATH, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            key = normalize_row(row)["key"]
            producer.produce(TOPIC, key=key, value=json.dumps(row), on_delivery=on_delivery)
            producer.poll(0)  # atiende los callbacks de entrega pendientes
            sent += 1

    producer.flush(30)
    log.info("%s filas publicadas en %s (%s errores)", sent, TOPIC, failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
