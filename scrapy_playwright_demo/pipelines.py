# scrapy_playwright_demo/pipelines.py
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Mapping

from itemadapter import ItemAdapter
from pydantic import ValidationError
from scrapy import signals
from scrapy.exceptions import DropItem

from scrapy_playwright_demo.items import PageDone, ProductItem
from scrapy_playwright_demo.sinks.base import PageSink
from scrapy_playwright_demo.sinks.registry import build_sink


# --------------------------------------------------------------------------- #
# Utils
# --------------------------------------------------------------------------- #
def _to_jsonable_dict(item: Any) -> Dict[str, Any]:
    if isinstance(item, ProductItem):
        # pydantic v2 → json mode already converts Decimal/Datetime
        return item.model_dump(mode="json")
    if hasattr(item, "__dataclass_fields__"):
        return asdict(item)
    return dict(ItemAdapter(item).asdict())


def _get_bool(settings, key, default):
    try:
        return settings.getbool(key, default)  # Scrapy Settings
    except AttributeError:
        if hasattr(settings, "get"):
            return bool(settings.get(key, default))
        # Pydantic model
        attr = key.lower()
        return bool(getattr(settings, attr, default))


# --------------------------------------------------------------------------- #
# 1) Validation pipeline
# --------------------------------------------------------------------------- #
class ValidateProductPipeline:
    """Lightweight validation for ProductItem."""

    REQUIRED = ("title", "link", "currency", "page")

    def process_item(self, item, spider):
        # Do not try to validate PageDone
        if isinstance(item, PageDone):
            return item

        # If not a ProductItem, try to validate it
        if not isinstance(item, ProductItem):
            try:
                raw = ItemAdapter(item).asdict()
                item = ProductItem.model_validate(raw)
            except ValidationError as e:
                raise DropItem(f"ProductItem validation error: {e}")

        # From here on, we always have a ProductItem
        data = item.model_dump(mode="python")

        # Required fields
        for field in self.REQUIRED:
            if data.get(field) in (None, ""):
                raise DropItem(f"Missing required field: {field}")

        # Rule: if discounted > original → swap
        now = data.get("price_discounted")
        orig = data.get("price_original")
        if now is not None and orig is not None and Decimal(str(now)) > Decimal(str(orig)):
            # swap in the model itself
            item.price_discounted, item.price_original = item.price_original, item.price_discounted
            if spider:
                spider.logger.debug("Swapping prices because discounted > original")

        return item


# --------------------------------------------------------------------------- #
# 2) Generic Per-page sink pipeline
# --------------------------------------------------------------------------- #
class PerPageSinkPipeline:
    """
    Generic per-page buffering pipeline writing through a PageSink.
    """

    def __init__(self, sink: PageSink, drop_missing_page: bool = True):
        self.sink = sink
        self.drop_missing_page = drop_missing_page
        self.buffer: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._settings: Mapping[str, Any] = {}

    @classmethod
    def from_crawler(cls, crawler):
        container = crawler.settings.get("CONTAINER")
        if container is None:
            raise RuntimeError("DI Container not found in settings. Make sure settings.CONTAINER is set.")
        sink = container.page_sink()
        drop_missing_page = _get_bool(crawler.settings, "PAGE_DROP_MISSING_FIELD", True)
        pipe = cls(
            sink=sink,
            drop_missing_page=drop_missing_page,
        )
        pipe._settings = crawler.settings
        crawler.signals.connect(pipe.spider_opened, signals.spider_opened)
        crawler.signals.connect(pipe.close_spider, signals.spider_closed)
        return pipe

    # Not strictly needed for file sink, but keep the hook in case
    def spider_opened(self, spider):
        pass

    def close_spider(self, spider):
        # Flush any page left in the buffer
        now = datetime.now(UTC).isoformat()
        for page_no in list(self.buffer.keys()):
            self._flush_page(page_no, now)

    # Core hook
    def process_item(self, item, spider):
        # If the end-of-page marker arrives → flush
        if isinstance(item, PageDone):
            self._flush_page(str(item.page), item.finished_at.isoformat())
            return item

        # Normal item
        page_no: str | None = None
        if isinstance(item, ProductItem):
            page_no = str(item.page)
        else:
            page_no = self._get_page_from_generic_item(item)

        drop_missing = (
            self.drop_missing_page
            if self.drop_missing_page is not None
            else bool(self._settings.get("PAGE_DROP_MISSING_FIELD", True))
        )

        if page_no is None:
            msg = "Item missing required 'page' field"
            if drop_missing:
                raise DropItem(msg)
            if spider:
                spider.logger.warning("%s: %s", msg, item)
            return item

        self.buffer[page_no].append(_to_jsonable_dict(item))
        return item

    # Helpers
    def _flush_page(self, page_no: str, finished_at: str):
        items = self.buffer.pop(page_no, [])
        if not items:
            return

        # Delegate to the sink. It will handle compression, idempotency, etc.
        self.sink.write_page(
            items=items,
            page=page_no,
            finished_at=finished_at,
            settings=self._settings,
        )

    @staticmethod
    def _get_page_from_generic_item(item: Any) -> str | None:
        try:
            return str(ItemAdapter(item).get("page"))
        except Exception:
            return None
