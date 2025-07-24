import pytest
from decimal import Decimal
from scrapy.selector import Selector
from scrapy_playwright_demo.spiders.zalando import ZalandoSpider
from scrapy_playwright_demo.spiders.base import PlaywrightListingSpider

@pytest.mark.parametrize(
    "html,expected",
    [
        ("<span>1.199,95 €</span>", [Decimal("1199.95")]),
        ("<span>99,90 €</span>", [Decimal("99.90")]),
        ("<span>1.199,95 €</span><span>99,90 €</span>", [Decimal("99.90"), Decimal("1199.95")]),
        ("<span>2.000,00 €</span>", [Decimal("2000.00")]),
        ("<span>1.000,00 €</span><span>2.000,00 €</span>", [Decimal("1000.00"), Decimal("2000.00")]),
    ],
)
def test_extract_prices(html, expected):
    sel = Selector(text=f"<div>{html}</div>")
    result = ZalandoSpider._extract_prices(sel)
    assert result == expected

@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://www.example.com/list?p=1", 1),
        ("https://www.example.com/list?p=5", 5),
        ("https://www.example.com/list", 1),
        ("https://www.example.com/list?p=10&foo=bar", 10),
    ],
)
def test_page_number(url, expected):
    assert PlaywrightListingSpider._page_number(url) == expected 