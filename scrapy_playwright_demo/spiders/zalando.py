"""
ZalandoSpider — Scrapes Zalando’s men sneakers category with Scrapy‑Playwright.

* Accepts the cookie banner once using a persistent Playwright context
* Handles infinite scroll + numbered pagination (?p=N)
* Yields typed ProductItem objects (Decimal money)
* Emits PageDone(page=N, finished_at=...) so PerPageFilePipeline can flush one file per page
* Async‑compatible with Scrapy ≥ 2.13
"""

from __future__ import annotations

import html
from decimal import Decimal, InvalidOperation
from typing import Iterable

import scrapy
from scrapy_playwright.page import PageMethod

from scrapy_playwright_demo.constants import (
    PRICE_RE,
    PAGINATION_NEXT_SELECTOR,
)
from scrapy_playwright_demo.items import ProductItem, Currency
from .base import PlaywrightListingSpider
from scrapy_playwright_demo.config import app_settings
from scrapy_playwright_demo.retry import build_retry_policy
from scrapy_playwright_demo.utils.logging import get_logger

import logging

logger = logging.getLogger(__name__)


def safe_urljoin(response: scrapy.http.Response, card) -> str | None:
    """Return absolute product URL or None if missing."""
    href = card.css("a::attr(href)").get()
    if not href:
        logger.warning("Missing href for product card on page %s", response.url)
        return None
    return response.urljoin(href)


class ZalandoSpider(PlaywrightListingSpider):
    name = "zalando"
    NEXT_PAGE_SELECTOR = "a[data-testid='pagination-next']::attr(href)"
    start_urls = getattr(app_settings, "start_urls", ["https://www.zalando.es/zapatillas-hombre/"])

    custom_settings = {
        **PlaywrightListingSpider.custom_settings,
        # Validation + per-page persistence
        "ITEM_PIPELINES": {
            "scrapy_playwright_demo.pipelines.ValidateProductPipeline": 50,
            "scrapy_playwright_demo.pipelines.PerPageFilePipeline": 100,
        },
        # Per-page persistence options
        "PAGE_OUT_DIR": app_settings.page_out_dir,
        "PAGE_COMPRESS": app_settings.page_compress,
        "PAGE_IDEMPOTENT": app_settings.page_idempotent,
        "PAGE_DROP_MISSING_FIELD": app_settings.page_drop_missing_field,
    }

    # --------------------------------------------------------------------- #
    # Requests bootstrap (cookie click, persistent context, etc.)
    # --------------------------------------------------------------------- #
    def start_requests(self) -> Iterable[scrapy.Request]:
        meta = {
            "playwright": True,
            "playwright_context": "persistent",        # keep cookies/session/fingerprint
            "playwright_include_page": True,           # we need Page in parse()
            "playwright_page_methods": [
                PageMethod(
                    "click",
                    "button[data-testid='uc-accept-all-button']",
                    timeout=5_000,
                    strict=False,                      # ignore if banner not present
                ),
            ],
            "playwright_page_goto_kwargs": {
                "wait_until": "domcontentloaded",
                "timeout": 45_000,
            },
        }
        for url in self.start_urls:
            yield scrapy.Request(url, meta=meta, dont_filter=True)

    # --------------------------------------------------------------------- #
    # Helpers
    # --------------------------------------------------------------------- #
    @staticmethod
    def _extract_prices(sel) -> list[Decimal]:
        """Grab every price-like token inside the element and return sorted Decimals."""
        prices: set[Decimal] = set()
        texts = sel.xpath(".//span[contains(text(),'€')]/text()").getall()
        for txt in texts:
            txt = html.unescape(txt).replace("\xa0", " ")
            for raw in PRICE_RE.findall(txt):
                try:
                    prices.add(Decimal(raw.replace(".", "").replace(",", ".")))
                except InvalidOperation:
                    continue
        return sorted(prices)

    @staticmethod
    def _extract_title(sel) -> str:
        return " ".join(
            t.strip() for t in sel.css("header h3 span::text").getall() if t.strip()
        )

    # --------------------------------------------------------------------- #
    # Main callback
    # --------------------------------------------------------------------- #
    async def parse(self, response):
        # `rendered_page` is provided by PlaywrightListingSpider (context manager that
        # returns (page, rendered_response, timings) and ALWAYS closes the page).
        async with self.rendered_page(response) as (page, rendered, timings):
            page_no = self._page_number(rendered.url)

            # Extract product cards
            for card in rendered.css("article"):
                plist = self._extract_prices(card)
                price_now: Decimal | None = plist[0] if plist else None
                price_orig: Decimal | None = (
                    plist[-1] if len(plist) > 1 and plist[-1] != price_now else None
                )

                link = safe_urljoin(rendered, card)
                if not link:
                    continue

                yield ProductItem(
                    page=page_no,
                    title=self._extract_title(card),
                    price_discounted=price_now,
                    price_original=price_orig,
                    currency=Currency.EUR,
                    link=link,
                )

            # Mark this page as done so the pipeline can flush it
            yield self.emit_page_done(page_no)

            # Follow pagination
            next_href = self.get_next_page_href(rendered)
            if next_href:
                yield scrapy.Request(
                    rendered.urljoin(next_href),
                    meta={
                        "playwright": True,
                        "playwright_context": "persistent",
                        "playwright_include_page": True,
                    },
                    callback=self.parse,
                    errback=self.errback_timeout,
                    dont_filter=True,
                )

    def errback_timeout(self, failure):
        """Unified retry logic for Playwright timeouts using RetryPolicy."""
        from playwright._impl._errors import TimeoutError as PWTimeout
        request = failure.request
        policy = build_retry_policy(getattr(self, 'settings', None))
        attempt = request.meta.get("retry_attempt", 0)
        logger = get_logger(self, url=request.url, attempt=attempt)
        if failure.check(PWTimeout):
            if attempt < policy.max_retries:
                delay = policy.next_delay(attempt)
                new = request.copy()
                new.meta["retry_attempt"] = attempt + 1
                new.meta["download_delay"] = delay
                new.dont_filter = True
                logger.info("retrying_playwright_timeout", url=request.url, attempt=attempt+1, delay=delay)
                return new
            else:
                logger.warning("max_retries_exceeded_playwright", url=request.url)
        # If not handled, Scrapy will log the failure as usual
