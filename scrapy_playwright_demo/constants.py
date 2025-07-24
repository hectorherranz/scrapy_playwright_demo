import re

PRICE_RE = re.compile(r"\d{1,3}(?:\.\d{3})*,\d{2}")  # 1.199,95  99,90

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

PAGINATION_NEXT_SELECTOR = "a[data-testid='pagination-next']::attr(href)" 