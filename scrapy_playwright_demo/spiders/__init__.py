# scrapy_playwright_demo/spiders/__init__.py
from .zalando import ZalandoSpider
from .base import PlaywrightListingSpider

__all__ = [
    "ZalandoSpider",
    "PlaywrightListingSpider",
]
