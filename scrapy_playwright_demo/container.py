"""
Container for dependency injection in scrapy_playwright_demo.

Lifecycles:
- retry_policy: Singleton per process (memoized)
- page_sink: Singleton per process (memoized)
- logger: Per spider (stateless factory, new instance per call)

Usage:
    container = Container(app_settings, crawler_settings)
    retry_policy = container.retry_policy()
    page_sink = container.page_sink()
    logger = container.logger(spider=spider)
"""
from typing import Callable, Any, Optional, Protocol
from uuid import uuid4
import structlog
from scrapy_playwright_demo.config import AppSettings
from scrapy_playwright_demo.retry import build_retry_policy, RetryPolicy
from scrapy_playwright_demo.sinks.base import PageSink
from scrapy_playwright_demo.utils.logging import get_logger

# (Optional) Minimal Protocol for PageSink for typing
class PageSinkProto(Protocol):
    def open(self) -> None: ...
    def write_page(self, page_number: int, items: list[dict]) -> None: ...
    def close(self) -> None: ...

class Container:
    def __init__(
        self,
        app_settings,
        crawler_settings=None,
        sink_factory: Optional[Callable[[Any], PageSinkProto]] = None,
    ):
        self.app_settings = app_settings
        self.crawler_settings = crawler_settings
        self._page_sink = None
        self._retry_policy = None
        self._sink_factory = sink_factory

    def retry_policy(self) -> RetryPolicy:
        if self._retry_policy is None:
            if self.crawler_settings is not None:
                self._retry_policy = build_retry_policy(self.crawler_settings)
            else:
                self._retry_policy = build_retry_policy(self.app_settings)
        return self._retry_policy

    def page_sink(self):
        if self._page_sink is None:
            if self._sink_factory is None:
                # Import at runtime for monkeypatch compatibility
                from scrapy_playwright_demo.sinks import registry
                factory = registry.build_sink
            else:
                factory = self._sink_factory
            self._page_sink = factory(self.app_settings)
        return self._page_sink

    def logger(self, spider=None, **extra):
        # Always return a fresh BoundLogger instance
        logger = get_logger(spider, **extra)
        return logger.bind(instance=str(uuid4())) 