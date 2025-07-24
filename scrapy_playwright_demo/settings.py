# settings.py

from scrapy_playwright_demo.config import app_settings  # noqa: F401  (must be imported before Scrapy reads settings)
import scrapy_playwright_demo.bootstrap  # noqa: F401

# -----------------
# Core settings
# -----------------
BOT_NAME = app_settings.bot_name
SPIDER_MODULES = app_settings.spider_modules
NEWSPIDER_MODULE = app_settings.spider_modules[0]
ROBOTSTXT_OBEY = False
LOG_LEVEL = app_settings.log_level

# Recommended for Scrapy + Playwright (optional if set elsewhere)
# TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

# -----------------
# Playwright integration
# -----------------
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
PLAYWRIGHT_BROWSER_TYPE = app_settings.playwright_browser_type
PLAYWRIGHT_LAUNCH_OPTIONS = {"headless": app_settings.playwright_headless}
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = app_settings.playwright_default_navigation_timeout_ms
PLAYWRIGHT_MAX_CONTEXTS = app_settings.playwright_max_contexts
PLAYWRIGHT_MAX_PAGES_PER_CONTEXT = app_settings.playwright_max_pages_per_context

# -----------------
# Throttling / Retries
# -----------------
AUTOTHROTTLE_ENABLED = app_settings.autothrottle_enabled
AUTOTHROTTLE_TARGET_CONCURRENCY = app_settings.autothrottle_target_concurrency
RETRY_TIMES = app_settings.retry_times
RETRY_HTTP_CODES = app_settings.retry_http_codes

# -----------------
# Middlewares
# -----------------
DOWNLOADER_MIDDLEWARES = {
    "scrapy_playwright_demo.middlewares.RotatingUserAgentAndProxyMiddleware": 543,
    # If you have your CustomRetryMiddleware enabled, leave it. If not, remove or fix the path.
    "scrapy_playwright_demo.middlewares.retry.CustomRetryMiddleware": 550,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
}

# -----------------
# Pipelines
# -----------------
ITEM_PIPELINES = {
    "scrapy_playwright_demo.pipelines.ValidateProductPipeline": 50,
    # New generic pipeline based on PageSink
    "scrapy_playwright_demo.pipelines.PerPageSinkPipeline": 100,
}

# -----------------
# Page sink config (used by PerPageSinkPipeline and sink implementations)
# -----------------
PAGE_SINK = app_settings.page_sink  # "file", "kafka", "s3", ...
PAGE_OUT_DIR = app_settings.page_out_dir
PAGE_COMPRESS = app_settings.page_compress
PAGE_IDEMPOTENT = app_settings.page_idempotent
PAGE_DROP_MISSING_FIELD = app_settings.page_drop_missing_field

PAGE_KAFKA_TOPIC = app_settings.page_kafka_topic
PAGE_KAFKA_BOOTSTRAP = app_settings.page_kafka_bootstrap
PAGE_S3_TEMPLATE = app_settings.page_s3_template

# -----------------
# UA / Proxies
# -----------------
ROTATING_UA_LIST = app_settings.rotating_ua_list
PROXY_LIST = app_settings.proxy_list

# -----------------
# Resumable jobs
# -----------------
JOBDIR = app_settings.jobdir
