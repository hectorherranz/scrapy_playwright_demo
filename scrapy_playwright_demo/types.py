from typing import TypedDict, Literal, Optional

class PlaywrightMeta(TypedDict, total=False):
    playwright: Literal[True]
    playwright_include_page: bool
    playwright_context: str
    playwright_page: object  # cannot type the real Playwright Page without depending on it here
    playwright_page_methods: list
    playwright_page_goto_kwargs: dict[str, object]
    retry_attempt: int 