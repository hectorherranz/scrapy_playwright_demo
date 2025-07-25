from __future__ import annotations

from typing import Mapping, Any

from scrapy.settings import Settings

from .file import FileSink
from .base import PageSink

# (Opcional) cuando implementes KafkaSink y S3Sink, impórtalos aquí y añádelos al registro.
# from .kafka import KafkaSink
# from .s3 import S3Sink

from collections.abc import Mapping

def _get(settings, key: str, default=None):
    # 1) Scrapy Settings or dict-like
    if hasattr(settings, "get"):
        try:
            return settings.get(key, default)
        except Exception:
            pass
    if isinstance(settings, Mapping):
        return settings.get(key, default)
    # 2) Pydantic settings object (AppSettings)
    # Keys come in UPPER_SNAKE_CASE -> turn into lower_snake_case attr
    attr = key.lower()
    return getattr(settings, attr, default)


def build_sink(settings) -> PageSink:
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
