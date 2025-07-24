from __future__ import annotations

from typing import Mapping, Any

from scrapy.settings import Settings

from .file import FileSink
from .base import PageSink

# (Opcional) cuando implementes KafkaSink y S3Sink, impórtalos aquí y añádelos al registro.
# from .kafka import KafkaSink
# from .s3 import S3Sink


def _get(settings: Mapping[str, Any] | Settings, key: str, default=None):
    if hasattr(settings, "get"):
        try:
            return settings.get(key, default)
        except TypeError:
            v = settings.get(key)
            return default if v is None else v
    return settings.get(key, default)  # type: ignore[arg-type]


def build_sink(settings: Mapping[str, Any] | Settings) -> PageSink:
    sink_name = str(_get(settings, "PAGE_SINK", "file")).lower()

    if sink_name == "file":
        return FileSink(
            out_dir=_get(settings, "PAGE_OUT_DIR", "out/products"),
            compress=bool(_get(settings, "PAGE_COMPRESS", True)),
            idempotent=bool(_get(settings, "PAGE_IDEMPOTENT", True)),
        )

    # if sink_name == "kafka":
    #     return KafkaSink(
    #         topic=_get(settings, "PAGE_KAFKA_TOPIC", "scrapy_pages"),
    #         bootstrap_servers=_get(settings, "PAGE_KAFKA_BOOTSTRAP", "localhost:9092"),
    #     )
    # if sink_name == "s3":
    #     return S3Sink(template=_get(settings, "PAGE_S3_TEMPLATE", "s3://bucket/prefix/page-{page}.jl.gz"))

    raise ValueError(f"Unknown PAGE_SINK: {sink_name}")


__all__ = ["build_sink"]
