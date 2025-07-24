# tests/conftest.py
from scrapy.http import HtmlResponse, Request
import pytest

@pytest.fixture
def fake_response():
    """
    Returns a factory function to build HtmlResponse objects easily.

    Usage:
        r = fake_response("https://foo?p=1", "<div>hi</div>")
    """
    def _make(url: str, html: str) -> HtmlResponse:
        request = Request(url=url)
        return HtmlResponse(url=url, body=html.encode("utf-8"), encoding="utf-8", request=request)
    return _make
