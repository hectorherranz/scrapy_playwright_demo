import pytest
from scrapy_playwright_demo.container import Container
from scrapy_playwright_demo.config import AppSettings
from scrapy_playwright_demo.sinks.fake import FakeSink
from scrapy_playwright_demo.sinks.base import PageSink
from scrapy_playwright_demo.retry import RetryPolicy

class DummySettings(dict):
    pass

def test_container_singleton_behavior(monkeypatch):
    app_settings = AppSettings()
    container = Container(app_settings)

    # Patch build_sink to always return a FakeSink
    monkeypatch.setattr(
        "scrapy_playwright_demo.sinks.registry.build_sink",
        lambda settings: FakeSink(),
    )
    sink1 = container.page_sink()
    sink2 = container.page_sink()
    assert sink1 is sink2  # Memoized singleton
    assert isinstance(sink1, FakeSink)

    # Patch build_retry_policy to always return a fixed RetryPolicy
    monkeypatch.setattr(
        "scrapy_playwright_demo.retry.build_retry_policy",
        lambda settings: RetryPolicy(
            max_retries=1, backoff_base=1.0, backoff_cap=1.0, jitter=0.0, retry_http_codes={500}, retry_exceptions=(Exception,)
        ),
    )
    policy1 = container.retry_policy()
    policy2 = container.retry_policy()
    assert policy1 is policy2  # Memoized singleton
    assert isinstance(policy1, RetryPolicy)


def test_container_logger_factory():
    app_settings = AppSettings()
    container = Container(app_settings)
    logger1 = container.logger()
    logger2 = container.logger()
    assert logger1 is not None
    assert logger1 != logger2  # Should be new structlog BoundLogger each call 