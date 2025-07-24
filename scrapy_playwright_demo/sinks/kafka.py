import json
from decimal import Decimal
from dataclasses import asdict
from datetime import datetime
from typing import Iterable, Mapping, Any
from .base import PageSink

class KafkaSink(PageSink):
    _producer = None

    @staticmethod
    def _json_default(o):
        if isinstance(o, Decimal):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        if hasattr(o, "__dataclass_fields__"):
            return asdict(o)
        raise TypeError(f"Type {type(o)} not serializable")

    def write_page(
        self,
        items: Iterable[dict[str, Any]],
        page: str,
        finished_at: str,
        settings: Mapping[str, Any],
    ) -> None:
        try:
            from kafka import KafkaProducer
        except ImportError as e:
            raise RuntimeError("PAGE_SINK=kafka but kafka-python is not installed.") from e
        topic = settings.get("PAGE_KAFKA_TOPIC", "scrapy_pages")
        bootstrap_servers = settings.get("PAGE_KAFKA_BOOTSTRAP", "localhost:9092")
        if KafkaSink._producer is None:
            KafkaSink._producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=KafkaSink._json_default).encode("utf-8"),
            )
        for obj in items:
            KafkaSink._producer.send(topic, obj)
        KafkaSink._producer.send(topic, {"page": page, "finished_at": finished_at, "type": "done"})
        KafkaSink._producer.flush() 