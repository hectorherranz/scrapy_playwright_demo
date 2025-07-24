from abc import ABC, abstractmethod
from typing import Iterable, Mapping, Any

class PageSink(ABC):
    @abstractmethod
    def write_page(
        self,
        items: Iterable[dict[str, Any]],
        page: str,
        finished_at: str,
        settings: Mapping[str, Any],
    ) -> None:
        """Write a page of items to the sink."""
        pass 