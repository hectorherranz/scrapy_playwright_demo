import os
import threading
import logging
import structlog
from scrapy import signals
from scrapy.utils.project import get_project_settings
from scrapy_playwright_demo.config import app_settings

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Validate early (so Scrapy fails-fast with a clear message)
app_settings.validate_required()

# Push config into Scrapy settings if running in a Scrapy context
try:
    import scrapy
    from scrapy.utils.project import get_project_settings
    _scrapy_settings = get_project_settings()
    # Map AppSettings fields to Scrapy settings
    _scrapy_settings.set("BOT_NAME", app_settings.bot_name)
    _scrapy_settings.set("SPIDER_MODULES", app_settings.spider_modules)
    _scrapy_settings.set("PLAYWRIGHT_BROWSER_TYPE", app_settings.playwright_browser_type)
    _scrapy_settings.set("PLAYWRIGHT_LAUNCH_OPTIONS", app_settings.playwright_launch_options)
    _scrapy_settings.set("PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT", app_settings.playwright_default_navigation_timeout)
    _scrapy_settings.set("PLAYWRIGHT_MAX_CONTEXTS", app_settings.playwright_max_contexts)
    _scrapy_settings.set("PLAYWRIGHT_MAX_PAGES_PER_CONTEXT", app_settings.playwright_max_pages_per_context)
    _scrapy_settings.set("AUTOTHROTTLE_ENABLED", app_settings.autothrottle_enabled)
    _scrapy_settings.set("AUTOTHROTTLE_TARGET_CONCURRENCY", app_settings.autothrottle_target_concurrency)
    if app_settings.user_agent:
        _scrapy_settings.set("USER_AGENT", app_settings.user_agent)
    _scrapy_settings.set("ROTATING_UA_LIST", app_settings.rotating_ua_list)
    if app_settings.proxy_url:
        _scrapy_settings.set("PROXY_URL", app_settings.proxy_url)
    _scrapy_settings.set("ITEM_PIPELINES", app_settings.item_pipelines)
    _scrapy_settings.set("PAGE_SINK", app_settings.page_sink)
    _scrapy_settings.set("PAGE_OUT_DIR", app_settings.page_out_dir)
    _scrapy_settings.set("PAGE_COMPRESS", app_settings.page_compress)
    _scrapy_settings.set("PAGE_IDEMPOTENT", app_settings.page_idempotent)
    _scrapy_settings.set("PAGE_DROP_MISSING_FIELD", app_settings.page_drop_missing_field)
    if app_settings.page_kafka_topic:
        _scrapy_settings.set("PAGE_KAFKA_TOPIC", app_settings.page_kafka_topic)
    if app_settings.page_kafka_bootstrap:
        _scrapy_settings.set("PAGE_KAFKA_BOOTSTRAP", app_settings.page_kafka_bootstrap)
    if app_settings.page_s3_template:
        _scrapy_settings.set("PAGE_S3_TEMPLATE", app_settings.page_s3_template)
    if app_settings.prometheus_port:
        _scrapy_settings.set("PROMETHEUS_PORT", app_settings.prometheus_port)
    _scrapy_settings.set("STATS_CLASS", app_settings.stats_class)
    if app_settings.sentry_dsn:
        _scrapy_settings.set("SENTRY_DSN", app_settings.sentry_dsn)
    _scrapy_settings.set("RETRY_HTTP_CODES", app_settings.retry_http_codes)
    _scrapy_settings.set("RETRY_TIMES", app_settings.retry_times)
    _scrapy_settings.set("ROBOTSTXT_OBEY", app_settings.robotstxt_obey)
except Exception as e:
    # Not running in Scrapy context, or settings already set
    pass

# Prometheus metrics server
try:
    from prometheus_client import start_http_server
except ImportError:
    start_http_server = None

# Sentry
try:
    import sentry_sdk
except ImportError:
    sentry_sdk = None

PROMETHEUS_PORT = os.environ.get("PROMETHEUS_PORT")
SENTRY_DSN = os.environ.get("SENTRY_DSN")

# Start Prometheus metrics server if enabled
def _start_prometheus():
    if start_http_server and PROMETHEUS_PORT:
        port = int(PROMETHEUS_PORT)
        t = threading.Thread(target=start_http_server, args=(port,), daemon=True)
        t.start()
        logging.getLogger(__name__).info(f"Prometheus metrics server started on :{port}")

# Initialize Sentry if DSN is set
def _init_sentry():
    if sentry_sdk and SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN)
        logging.getLogger(__name__).info("Sentry initialized")

# Configure structlog for JSON logs
def _init_structlog():
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(format="%(message)s", level=logging.INFO)

_start_prometheus()
_init_sentry()
_init_structlog() 