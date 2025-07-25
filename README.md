# Scrapy + Playwright Demo

**A strongly-typed, extensible Scrapy project powered by Playwright** to scrape JavaScript-heavy sites, with a clean configuration layer (Pydantic), pluggable page sinks (file / S3 / Kafka), centralized retry/backoff policy, and a lightweight dependency injection container.

---

## Table of Contents

- [Key Features](#key-features)  
- [Project Layout](#project-layout)  
- [Quick Start](#quick-start)  
  - [Run locally](#run-locally)  
  - [Run with Docker](#run-with-docker)
- [Configuration](#configuration)  
  - [Hierarchy & precedence](#hierarchy--precedence)  
  - [AppSettings (Pydantic)](#appsettings-pydantic)  
  - [Environment variables (.env)](#environment-variables-env)  
  - [Scrapy settings mapping](#scrapy-settings-mapping)
- [Dependency Injection Container](#dependency-injection-container)
- [Pipelines & Page Sinks](#pipelines--page-sinks)
- [Retry Policy](#retry-policy)
- [Observability](#observability)
- [Testing](#testing)
- [Common Issues & Troubleshooting](#common-issues--troubleshooting)
- [Development Guidelines](#development-guidelines)
- [Roadmap / Next Steps](#roadmap--next-steps)
- [License](#license)

---

## Key Features

- **Playwright integration** via `scrapy-playwright` to render and scrape JS-heavy pages.
- **Typed configuration** using **Pydantic Settings** (`AppSettings`) as the single source of truth.
- **DI container** to centralize construction of core services (e.g., `RetryPolicy`, `PageSink`), improving testability.
- **Pluggable, per-page “sinks”** (file, S3, Kafka — easily add your own) chosen at runtime by configuration.
- **Centralized retry/backoff policy** (`RetryPolicy` value object).
- **Structlog-based structured logging**, optional **Sentry** and **Prometheus** integration.
- **Validation-ready Pydantic Items** (DTOs) for clean, schema-enforced outputs.

---

## Project Layout

```
scrapy_playwright_demo/
├── scrapy_playwright_demo/
│   ├── __init__.py
│   ├── config.py                 # AppSettings (Pydantic) – the master config
│   ├── settings.py               # Scrapy settings adapter (maps AppSettings → Scrapy constants)
│   ├── bootstrap.py              # Initializes logging, Sentry, Prometheus, validates config
│   ├── container.py              # Lightweight DI container
│   ├── constants.py
│   ├── items.py                  # Pydantic items (domain DTOs)
│   ├── middlewares.py            # UA/Proxy rotation, retry/backoff, Playwright integration (via scrapy-playwright)
│   ├── pipelines.py              # Per-page pipeline delegating to a PageSink
│   ├── retry.py                  # RetryPolicy + builder (centralized backoff/jitter/http codes)
│   ├── sinks/                    # Strategy + Factory for persistence
│   │   ├── __init__.py
│   │   ├── base.py               # PageSink ABC / Protocol
│   │   ├── file.py               # FileSink implementation
│   │   ├── s3.py                 # (optional / skeleton) S3 sink
│   │   ├── kafka.py              # (optional / skeleton) Kafka sink
│   │   └── registry.py           # build_sink factory (selects sink by config)
│   ├── spiders/
│   │   ├── base.py               # BaseSpider: Template Method for Playwright helpers, pagination, etc.
│   │   └── zalando.py            # Example spider
│   └── utils/                    # Helpers (e.g., parsing, price normalization, etc.)
├── tests/
│   ├── test_container.py
│   ├── test_pipelines.py
│   └── ...
├── scrapy.cfg
├── requirements.txt / pyproject.toml
├── .env.example
└── README.md
```

---

## Quick Start

### Run locally

```bash
# 1) Create & activate a virtualenv
python -m venv .venv
source .venv/bin/activate

# 2) Install deps
pip install -r requirements.txt
# or: pip install -e .  (if you use pyproject.toml / setup.cfg)

# 3) Copy and edit your env
cp .env.example .env

# 4) Run a spider
scrapy crawl zalando -s LOG_LEVEL=INFO
```

### Run with Docker

```bash
# Tests (example target in docker-compose.yml)
docker compose run --rm tester

# Regular run
docker compose run --rm app scrapy crawl zalando
```

---

## Configuration

### Hierarchy & precedence

This project centralizes configuration in `AppSettings` (Pydantic). The effective order of precedence is:

1. **Defaults** defined in `AppSettings` fields.  
2. **`.env` file(s)** (e.g., `.env`, `.env.local`) loaded by Pydantic.  
3. **Process environment variables**.  
4. **Scrapy CLI overrides** (`scrapy crawl spider -s KEY=VALUE`) or direct changes in `settings.py` — **these always win** from Scrapy’s perspective.

`settings.py` maps the strongly-typed `AppSettings` fields into Scrapy’s expected UPPERCASE constants. That file also bootstraps logging and observability.

### AppSettings (Pydantic)

`config.py` defines **all** knobs you care about (Scrapy concurrency, Playwright headless, retry policy, sinks, observability, etc.). Examples:

```python
class AppSettings(BaseSettings):
    bot_name: str = "scrapy_playwright_demo"
    spider_modules: list[str] = ["scrapy_playwright_demo.spiders"]
    log_level: str = "INFO"

    # Playwright
    playwright_browser_type: Literal["chromium", "firefox", "webkit"] = "chromium"
    playwright_headless: bool = True
    playwright_page_timeout_ms: int = 30_000
    playwright_max_contexts: int = 1
    playwright_max_pages_per_context: int = 1

    # Retry/backoff
    retry_enabled: bool = True
    retry_http_codes: list[int] = [429, 500, 502, 503, 504]
    retry_times: int = 5
    retry_backoff_base: float = 1.5
    retry_backoff_max: float = 60.0
    retry_jitter: bool = True

    # Page sink
    page_sink: Literal["file", "s3", "kafka"] = "file"
    page_out_dir: str = "./data/pages"
    page_compress: bool = True
    page_s3_template: str = "s3://bucket/prefix/page-{page}.jl.gz"

    # Observability
    sentry_dsn: str | None = None
    prometheus_enabled: bool = False

    model_config = SettingsConfigDict(env_file=(".env", ".env.local"), env_file_encoding="utf-8")
```

### Environment variables (.env)

Create a `.env` from `.env.example`:

```env
# Logging
LOG_LEVEL=INFO

# Playwright
PLAYWRIGHT_BROWSER_TYPE=chromium
PLAYWRIGHT_HEADLESS=true

# Retry
RETRY_TIMES=5
RETRY_BACKOFF_BASE=1.5
RETRY_BACKOFF_MAX=60
RETRY_JITTER=true

# Page sink
PAGE_SINK=file
PAGE_OUT_DIR=./data/pages
PAGE_COMPRESS=true

# Observability
SENTRY_DSN=
PROMETHEUS_ENABLED=false
```

### Scrapy settings mapping

`settings.py`:

- Imports `app_settings` from `config.py`.
- Runs `bootstrap()` to set up logging/metrics/Sentry.
- Exposes all relevant Scrapy settings (e.g., `BOT_NAME`, `DOWNLOADER_MIDDLEWARES`, `ITEM_PIPELINES`, etc.) using values from `app_settings`.
- Injects the **DI container** (`CONTAINER`) into Scrapy’s settings so components can retrieve pre-built services.

---

## Dependency Injection Container

The **lightweight DI container** (`container.py`) centralizes construction of cross-cutting dependencies:

- `page_sink()` → returns a memoized `PageSink` (strategy chosen by config).
- `retry_policy()` → returns a memoized `RetryPolicy` (value object).
- `logger()` → returns a new bound structlog logger (per call) for better contextual logging (as enforced by tests).

It can also accept a **custom sink factory** for testing (e.g., a `FakeSink`), or import the default from `sinks.registry` at runtime so your tests can monkeypatch it cleanly.

Usage in Scrapy components:

```python
@classmethod
def from_crawler(cls, crawler):
    container = crawler.settings.get("CONTAINER")
    if not container:
        raise RuntimeError("DI Container not found in settings.")
    sink = container.page_sink()
    ...
```

---

## Pipelines & Page Sinks

### PerPageSinkPipeline (example)

- Validates **Pydantic items** (domain DTOs).
- Groups items **per page** and flushes on page boundary (e.g., when you emit a special “PageDone” signal/item).
- Delegates persistence to a **`PageSink`** (Strategy pattern), which you switch in config:
  - **FileSink**: writes `.jsonl` (optionally gzipped) to local disk.
  - **S3Sink**: (skeleton / example) writes to AWS S3 using a templated key (e.g., `page-{page}.jl.gz`).
  - **KafkaSink**: (skeleton / example) streams to Kafka.

### Adding a new sink

1. Implement `PageSink` ABC/Protocol in `sinks/your_sink.py`.
2. Register it in `sinks/registry.py` (map `PAGE_SINK="your_sink"` to your implementation).
3. Configure `PAGE_SINK=your_sink` in `.env`.

---

## Retry Policy

`retry.py` contains a **centralized** `RetryPolicy` (dataclass) + a builder (`build_retry_policy(settings)`) that:

- Defines retryable HTTP codes, exceptions, **exponential backoff with optional jitter**, and max caps.
- Is consumed by the downloader middleware(s) so the **retry logic is not scattered** all over the codebase.

---

## Observability

**bootstrap.py** activates:

- **structlog** (structured logs).
- **Sentry** (if `SENTRY_DSN` is provided).
- **Prometheus** (if enabled), to expose metrics like:
  - number of pages processed, batches written, retry counts, latency histograms, pool saturation for Playwright contexts, etc.

(You can bring in **OpenTelemetry** for tracing if you want end-to-end spans around Playwright rendering, parsing, and sink writes.)

---

## Testing

Run the full test suite:

```bash
pytest -q
# Or via Docker:
docker compose run --rm tester
```

### Contract tests for sinks

We recommend writing **contract tests** (already started in `tests/`) that run the same behavior suite against each `PageSink` implementation (file, s3, kafka, fake). This guarantees **idempotency, atomic writes, compression behavior**, etc., across sinks.

### Fakes / Mocks

Use a **FakeSink** (in-memory) injected through the container’s `sink_factory` for fast pipeline tests without touching the filesystem or external services.

---

## Common Issues & Troubleshooting

### 403 responses / consent walls (e.g., Zalando)

- Add a **request interception rule** (Playwright route) to **block tracking endpoints** (e.g., `gtm`, analytics) to reduce noise and potential 403s.
- Programmatically **accept or set consent cookies** before navigating to the primary URLs, or handle `/api/consents` routes explicitly.
- Provide a **realistic user-agent** and language/locale headers.
- Consider **headful** runs for debugging (`PLAYWRIGHT_HEADLESS=false`) and **stealth-like** adjustments to avoid obvious headless fingerprints.

### `BrowserContext.new_page: Connection closed while reading from the driver`

- Ensure **graceful shutdown** on SIGINT: wrap Playwright close calls with `asyncio.gather(..., return_exceptions=True)`.
- Cap **contexts/pages** (via `playwright_max_contexts`, `playwright_max_pages_per_context`) and expose metrics to detect leaks.
- Re-launch the browser if a context crashes (scrapy-playwright automatically retries to some extent, but you can add additional guards).

### SIGINT / shutdown noise

- Catch SIGINT early and signal Scrapy to exit.  
- Make pipeline/sink `close()` idempotent and defensive against already-closed contexts.

---

## Development Guidelines

- **Do not read Scrapy settings directly** inside business logic. Always go through `AppSettings` or the **DI container**.
- **Favor Protocols/ABCs** (`typing.Protocol`) for interfaces like `PageSink` to keep components swappable.
- **Keep domain objects (items, retry policy) free of Scrapy imports** to enable reuse in other runtimes (CLI workers, APIs, etc.).
- **Write contract tests** for interchangeable parts (sinks, retry policies).

---

## Roadmap / Next Steps

Planned/Recommended improvements:

1. **Full domain vs. infrastructure split** (`domain/` vs `infra/`) to enable clean architecture.
2. **Circuit breakers / rate limiting** per host or proxy to protect resources and recover faster from 429/500 storms.
3. **Event bus (signals)** for “page done”, “sink write”, “retry happened”, etc., so you can attach metrics/alerts without modifying core code.
4. **Plugin system for sinks/middlewares** using `entry_points` so external teams can add integrations without touching core.
5. **Automatic configuration docs**: generate Markdown/HTML from `AppSettings` (field name, type, default, env var, description).
6. **Schema versioning for items** (`schema_version` field) + migration helpers for downstream consumers.

---

## License

MIT (or your chosen license). See [LICENSE](LICENSE) for details.
