import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from scrapy.exceptions import DropItem

from scrapy_playwright_demo.items import ProductItem, Currency
from scrapy_playwright_demo.pipelines import ValidateProductPipeline, PerPageSinkPipeline
from scrapy_playwright_demo.sinks.file import FileSink
from scrapy_playwright_demo.sinks.fake import FakeSink
from scrapy_playwright_demo.container import Container
from scrapy_playwright_demo.config import AppSettings


class DummyCrawler:
    def __init__(self, settings):
        self.settings = settings
        self.signals = type("Signals", (), {"connect": lambda *a, **k: None})()


def make_settings(out_dir: str, compress: bool = True, idempotent: bool = True):
    # Lightweight mapping that behaves like a dict
    return {
        "PAGE_OUT_DIR": out_dir,
        "PAGE_COMPRESS": compress,
        "PAGE_IDEMPOTENT": idempotent,
        "PAGE_DROP_MISSING_FIELD": True,
        "PAGE_SINK": "file",
    }


@pytest.fixture
def valid_item():
    return ProductItem(
        page=1,
        title="Test Shoe",
        price_discounted=Decimal("10.0"),
        price_original=Decimal("20.0"),
        currency=Currency.EUR,
        link="http://example.com",
    )


def test_validate_missing_field(valid_item: ProductItem):
    pipeline = ValidateProductPipeline()
    item = valid_item.model_copy()
    item.title = ""
    with pytest.raises(DropItem, match="Missing required field: title"):
        pipeline.process_item(item, spider=None)


def test_validate_price_swap(valid_item: ProductItem):
    pipeline = ValidateProductPipeline()
    item = valid_item.model_copy()
    item.price_discounted = Decimal("30.0")
    item.price_original = Decimal("20.0")
    result = pipeline.process_item(item, spider=None)
    assert result.price_discounted == Decimal("20.0")
    assert result.price_original == Decimal("30.0")


def test_perpage_filesink_idempotency(tmp_path, valid_item: ProductItem):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    settings = make_settings(str(out_dir), compress=True, idempotent=True)

    sink = FileSink()
    pipeline = PerPageSinkPipeline(sink)
    pipeline._settings = settings

    page = "1"
    finished_at = datetime.datetime.now(datetime.UTC).isoformat()
    pipeline.buffer[page] = [valid_item.model_dump(mode="json")]

    pipeline._flush_page(page, finished_at)

    data_path = out_dir / f"page-{page}.jl.gz"
    done_path = out_dir / f"page-{page}.done"
    assert data_path.exists()
    assert done_path.exists()

    # Second flush should be skipped (idempotent)
    pipeline.buffer[page] = [valid_item.model_dump(mode="json")]
    pipeline._flush_page(page, finished_at)

    assert data_path.exists()
    assert done_path.exists()


def test_perpage_filesink_flush_on_close(tmp_path, valid_item: ProductItem):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    settings = make_settings(str(out_dir), compress=True, idempotent=False)

    sink = FileSink()
    pipeline = PerPageSinkPipeline(sink)
    pipeline._settings = settings

    page = "2"
    pipeline.buffer[str(page)] = [valid_item.model_dump(mode="json")]

    pipeline.close_spider(spider=None)

    data_path = out_dir / f"page-{page}.jl.gz"
    done_path = out_dir / f"page-{page}.done"
    assert data_path.exists()
    assert done_path.exists()


def test_per_page_sink_pipeline_uses_container(monkeypatch):
    fake_sink = FakeSink()
    app_settings = AppSettings()
    container = Container(app_settings)
    monkeypatch.setattr(container, "page_sink", lambda: fake_sink)
    settings = {"CONTAINER": container, "PAGE_DROP_MISSING_FIELD": True}
    crawler = DummyCrawler(settings)
    pipe = PerPageSinkPipeline.from_crawler(crawler)
    assert pipe.sink is fake_sink
