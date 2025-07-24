import pytest

from scrapy_playwright_demo.spiders.base import PlaywrightListingSpider

class DummySpider(PlaywrightListingSpider):
    name = "dummy"

@pytest.mark.parametrize(
    "html,url,expected",
    [
        ("<a data-testid='pagination-next' href='/page2'>Next</a>", "https://foo/list?p=1", "/page2"),
        ("<link rel='next' href='/page3' />", "https://foo/list?p=2", "/page3"),
        ("<span data-testid='pagination-total-pages'>3</span>", "https://foo/list?p=2", "https://foo/list?p=3"),
        ("<span data-testid='pagination-total-pages'>2</span>", "https://foo/list?p=2", None),
    ],
)
def test_get_next_page_href(fake_response, html, url, expected):
    spider = DummySpider()
    response = fake_response(url, f"<html><body>{html}</body></html>")
    assert spider.get_next_page_href(response) == expected

def test_extract_total_pages(fake_response):
    spider = DummySpider()
    r1 = fake_response("https://foo/list?p=1", "<span data-testid='pagination-total-pages'>5</span>")
    assert spider.extract_total_pages(r1) == 5
    r2 = fake_response("https://foo/list?p=2", "<div>Page 2 of 7</div>")
    assert spider.extract_total_pages(r2) == 7
