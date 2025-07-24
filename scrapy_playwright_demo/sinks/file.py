# scrapy_playwright_demo/sinks/file.py
from __future__ import annotations

import gzip
import json
import os
from datetime import datetime
from decimal import Decimal
from typing import Any, Iterable, Mapping

from .base import PageSink


def _json_default(o: Any):
    if isinstance(o, Decimal):
        return str(o)
    if isinstance(o, datetime):
        # ISO sin perder zona si la hubiera
        return o.isoformat()
    # pydantic v2 dicts ya vienen serializables
    raise TypeError(f"Type {type(o)} not serializable")


class FileSink(PageSink):
    """
    File-based sink that writes:
      page-{N}.jl[.gz]  +  page-{N}.done

    El constructor acepta argumentos opcionales para que los tests puedan
    instanciarlo como `FileSink()` sin romper. Si no se pasan, se toman de
    `settings` en tiempo de ejecución.
    """

    def __init__(
        self,
        out_dir: str | None = None,
        compress: bool | None = None,
        idempotent: bool | None = None,
    ) -> None:
        self._out_dir = out_dir
        self._compress = compress
        self._idempotent = idempotent

    # Helpers ---------------------------------------------------------------

    @staticmethod
    def _get_bool(settings: Mapping[str, Any], key: str, default: bool) -> bool:
        val = settings.get(key, default)
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in {"1", "true", "yes", "on"}
        return bool(val)

    def _resolve_config(self, settings: Mapping[str, Any]) -> tuple[str, bool, bool]:
        out_dir = self._out_dir or settings.get("PAGE_OUT_DIR", "out/products")
        compress = (
            self._compress
            if self._compress is not None
            else self._get_bool(settings, "PAGE_COMPRESS", True)
        )
        idempotent = (
            self._idempotent
            if self._idempotent is not None
            else self._get_bool(settings, "PAGE_IDEMPOTENT", True)
        )
        return out_dir, compress, idempotent

    @staticmethod
    def _paths(out_dir: str, page: str, compress: bool) -> tuple[str, str]:
        suffix = ".jl.gz" if compress else ".jl"
        data_path = os.path.join(out_dir, f"page-{page}{suffix}")
        done_path = os.path.join(out_dir, f"page-{page}.done")
        return data_path, done_path

    # API -------------------------------------------------------------------

    def write_page(
        self,
        items: Iterable[dict[str, Any]],
        page: str,
        finished_at: str,
        settings: Mapping[str, Any],
    ) -> None:
        out_dir, compress, idempotent = self._resolve_config(settings)
        os.makedirs(out_dir, exist_ok=True)

        data_path, done_path = self._paths(out_dir, page, compress)

        # Idempotencia: si .done existe, salimos (esto también lo puede
        # controlar la pipeline antes de llamar, pero aquí es seguro repetirlo)
        if idempotent and os.path.exists(done_path):
            return

        open_fn = gzip.open if compress else open
        mode = "at" if compress else "a"  # gzip.open soporta "at"
        with open_fn(data_path, mode, encoding="utf-8") as f:
            for obj in items:
                f.write(json.dumps(obj, ensure_ascii=False, default=_json_default) + "\n")

        with open(done_path, "w", encoding="utf-8") as f:
            f.write(finished_at + "\n")
