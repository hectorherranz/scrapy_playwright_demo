import json
from decimal import Decimal
from dataclasses import asdict
from datetime import datetime
from typing import Iterable, Mapping, Any
from .base import PageSink

class S3Sink(PageSink):
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
            from smart_open import open as smart_open
            import boto3  # noqa: F401
        except ImportError as e:
            raise RuntimeError("PAGE_SINK=s3 but smart_open/boto3 are not installed.") from e
        template = settings.get("PAGE_S3_TEMPLATE", "s3://bucket/prefix/page-{page}.jl.gz")
        path = template.format(page=page)
        with smart_open(path, "wt", encoding="utf8") as f:
            for obj in items:
                f.write(json.dumps(obj, ensure_ascii=False, default=S3Sink._json_default) + "\n")
        done_path = path.replace(".jl.gz", ".done")
        with smart_open(done_path, "wt", encoding="utf8") as f:
            f.write(finished_at + "\n") 