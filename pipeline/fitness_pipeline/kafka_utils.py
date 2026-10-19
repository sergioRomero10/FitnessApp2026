"""Utilidades comunes de Kafka: configuración y creación del topic."""

import logging
import os
import time

from confluent_kafka import KafkaException
from confluent_kafka.admin import AdminClient, NewTopic

log = logging.getLogger(__name__)

BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPIC = os.environ.get("KAFKA_TOPIC", "foods.catalog")


def ensure_topic(retries: int = 30, delay: float = 2.0) -> None:
    """Crea el topic si no existe.

    Sustituye a los time.sleep(20)/time.sleep(30) del original: en vez de esperar un tiempo
    fijo "por si acaso", se reintenta hasta que Kafka responde.
    """
    admin = AdminClient({"bootstrap.servers": BOOTSTRAP})
    for attempt in range(1, retries + 1):
        try:
            if TOPIC in admin.list_topics(timeout=5).topics:
                return
            futures = admin.create_topics([NewTopic(TOPIC, num_partitions=1, replication_factor=1)])
            futures[TOPIC].result()
            log.info("Topic %s creado", TOPIC)
            return
        except KafkaException as exc:
            if "TOPIC_ALREADY_EXISTS" in str(exc):
                return
            log.warning("Kafka no disponible (intento %s/%s): %s", attempt, retries, exc)
            time.sleep(delay)
    raise RuntimeError(f"No se pudo conectar con Kafka en {BOOTSTRAP}")
