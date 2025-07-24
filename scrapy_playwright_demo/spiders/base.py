from __future__ import annotations

import urllib.parse
from datetime import datetime, UTC
from scrapy import Spider, Request
from scrapy_playwright.page import PageMethod
from scrapy_playwright_demo.items import PageDone
from scrapy_playwright_demo.constants import DEFAULT_USER_AGENT, PAGINATION_NEXT_SELECTOR
import time
from contextlib import asynccontextmanager
from typing import Any, Optional
from scrapy_playwright_demo.types import PlaywrightMeta
import logging
from scrapy_playwright_demo.config import app_settings
from scrapy_playwright_demo.utils.logging import get_logger

try:
    from prometheus_client import Histogram
    crawl_page_seconds = Histogram(
        "spider_crawl_page_seconds",
        "Time spent rendering a page",
        ["spider", "page"]
    )
except ImportError:
    crawl_page_seconds = None

def get_required_meta(meta: PlaywrightMeta, key: str) -> object:
    if key not in meta or meta[key] is None:
        raise KeyError(f"Missing required meta key: {key}")
    return meta[key]

def get_playwright_page(meta: PlaywrightMeta) -> object:
    if "playwright_page" not in meta or meta["playwright_page"] is None:
        raise KeyError("Missing required meta key: 'playwright_page'")
    return meta["playwright_page"]

class PlaywrightListingSpider(Spider):
    # By default, no specific selector; each spider defines its own.
    NEXT_PAGE_SELECTOR: str | None = None
    custom_settings = {
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": app_settings.playwright_default_navigation_timeout_ms,
        "AUTOTHROTTLE_ENABLED": app_settings.autothrottle_enabled,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": app_settings.autothrottle_target_concurrency,
    }

    def start_requests(self):
        meta = {
            "playwright": True,
            "playwright_context": "persistent",
            "playwright_include_page": True,
        }
        for url in getattr(self, "start_urls", []):
            yield Request(url, meta=meta, dont_filter=True)

    @staticmethod
    def _page_number(url: str) -> int:
        qs = urllib.parse.urlparse(url).query
        return int(urllib.parse.parse_qs(qs).get("p", ["1"])[0])

    async def _scroll_to_bottom(self, page, loops: int = 5):
        for _ in range(loops):
            await page.mouse.wheel(0, 10_000)
            await page.wait_for_timeout(800)

    def emit_page_done(self, page_no: int):
        return PageDone(page=page_no, finished_at=datetime.now(UTC))

    @asynccontextmanager
    async def rendered_page(self, response):
        meta: PlaywrightMeta = response.meta  # type: ignore
        page = get_playwright_page(meta)
        timings = {}
        t0 = time.perf_counter()
        try:
            await self._scroll_to_bottom(page)
            t1 = time.perf_counter()
            rendered_html = await page.content()
            t2 = time.perf_counter()
            timings["scroll"] = t1 - t0
            timings["render"] = t2 - t1
            timings["total"] = t2 - t0
            rendered = response.replace(body=rendered_html)
            yield page, rendered, timings
        finally:
            await page.close()
            if crawl_page_seconds:
                crawl_page_seconds.labels(
                    spider=getattr(self, "name", "unknown"),
                    page=str(self._page_number(response.url)),
                ).observe(timings.get("total", 0.0))

    def get_next_page_href(self, response, selector: str | None = None) -> Optional[str]:
        """
        Returns the href for the next page.
        Preference order:
          1) CSS selector (by parameter or defaults to Zalando)
          2) Direct XPath
          3) <link rel="next">
          4) Fallback: build ?p=current+1 if total pages is available.
        """
        sel = selector or self.NEXT_PAGE_SELECTOR or "a[data-testid='pagination-next']::attr(href)"

        # 1) CSS selector
        href = response.css(sel).get() if sel else None
        if href:
            return href
        # 2) Direct XPath
        href = response.xpath("//a[@data-testid='pagination-next']/@href").get()
        if href:
            return href
        # 3) link[rel=next]
        href = response.css('link[rel="next"]::attr(href)').get()
        if href:
            return href
        # 4) Fallback: build ?p=current+1 if total pages is available
        total = self.extract_total_pages(response)
        current = self._page_number(response.url)
        if total and current < total:
            parsed = urllib.parse.urlparse(response.url)
            qs = urllib.parse.parse_qs(parsed.query)
            qs["p"] = [str(current + 1)]
            new_query = urllib.parse.urlencode(qs, doseq=True)
            new_url = parsed._replace(query=new_query).geturl()
            return new_url
        return None

    def extract_total_pages(self, response) -> Optional[int]:
        # Try to extract total pages from a hint in the HTML (override for site-specific logic)
        # Example: <span data-testid="pagination-total-pages">5</span>
        val = response.css('[data-testid="pagination-total-pages"]::text').get()
        if val and val.isdigit():
            return int(val)
        # Try to find "Page X of Y"
        import re
        m = re.search(r'Page \d+ of (\d+)', response.text)
        if m:
            return int(m.group(1))
        return None 