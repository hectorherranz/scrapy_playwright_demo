from __future__ import annotations

from typing import List, Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, Field
from pathlib import Path

class AppSettings(BaseSettings):
    # ---- Scrapy basics ----
    bot_name: str = "scrapy_playwright_demo"
    spider_modules: List[str] = ["scrapy_playwright_demo.spiders"]
    log_level: str = "INFO"
    jobdir: str = "/data/state/zalando"

    # ---- Playwright ----
    playwright_browser_type: Literal["chromium", "firefox", "webkit"] = "chromium"
    playwright_headless: bool = True
    playwright_default_navigation_timeout_ms: int = 45_000
    playwright_max_contexts: int = 2
    playwright_max_pages_per_context: int = 4
    autoplay_scroll_loops: int = 5

    # ---- Throttling / retries ----
    autothrottle_enabled: bool = True
    autothrottle_target_concurrency: float = 2.0
    retry_max_retries: int = 5
    retry_backoff_base: float = 1.5
    retry_backoff_cap: float = 60.0
    retry_jitter: float = 0.3
    retry_http_codes: list[int] = [429, 500, 502, 503, 504]
    retry_exceptions: tuple = (Exception,)

    # ---- UA / Proxies ----
    rotating_ua_list: List[str] = [
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    ]
    proxy_list: List[str] = []  # optional

    # ---- Pipelines / per-page sink ----
    page_sink: Literal["file", "kafka", "s3"] = "file"
    page_out_dir: str = "/data/products"
    page_compress: bool = True
    page_idempotent: bool = True
    page_drop_missing_field: bool = True

    # Kafka
    page_kafka_topic: str = "scrapy_pages"
    page_kafka_bootstrap: str = "localhost:9092"

    # S3
    page_s3_template: str = "s3://bucket/prefix/page-{page}.jl.gz"

    # Observability toggles (disabled by default here)
    sentry_dsn: Optional[str] = None
    prometheus_enabled: bool = False

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        case_sensitive=False,
        extra="ignore",
    )

    def validate_required(self) -> None:
        if not self.rotating_ua_list:
            raise ValueError("ROTATING_UA_LIST must not be empty")

# Global singleton
app_settings = AppSettings() 