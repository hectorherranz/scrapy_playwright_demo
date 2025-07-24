from dataclasses import dataclass
import random
from typing import Iterable, Type, Set, Tuple

@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int
    backoff_base: float  # e.g. 1.5
    backoff_cap: float   # e.g. 60.0
    jitter: float        # 0..1
    retry_http_codes: Set[int]
    retry_exceptions: Tuple[type[Exception], ...]

    def next_delay(self, attempt: int) -> float:
        raw = min(self.backoff_cap, self.backoff_base ** attempt)
        return raw * (1 + random.random() * self.jitter)

# Helper to build from settings or AppSettings
from scrapy_playwright_demo.config import app_settings

def build_retry_policy(settings=None) -> RetryPolicy:
    s = settings or app_settings
    return RetryPolicy(
        max_retries=getattr(s, "retry_max_retries", 5),
        backoff_base=getattr(s, "retry_backoff_base", 1.5),
        backoff_cap=getattr(s, "retry_backoff_cap", 60.0),
        jitter=getattr(s, "retry_jitter", 0.3),
        retry_http_codes=set(getattr(s, "retry_http_codes", [429, 500, 502, 503, 504])),
        retry_exceptions=tuple(getattr(s, "retry_exceptions", (Exception,))),
    ) 