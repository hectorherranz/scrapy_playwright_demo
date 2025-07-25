from typing import Iterable, Mapping, Any
from .base import PageSink

class FakeSink(PageSink):
    """In-memory sink for testing. Stores pages in a dict."""
    def __init__(self):
        self.pages = {}

    def write_page(
        self,
        items: Iterable[dict[str, Any]],
        page: str,
        finished_at: str,
        settings: Mapping[str, Any],
    ) -> None:
        self.pages[page] = {
            "items": list(items),
            "finished_at": finished_at,
            "settings": dict(settings),
        } 