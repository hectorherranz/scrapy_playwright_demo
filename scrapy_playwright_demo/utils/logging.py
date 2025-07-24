import structlog
from scrapy import Spider
from typing import Any

def get_logger(spider: Spider | None = None, **extra: Any):
    bound = {}
    if spider is not None:
        bound["spider"] = getattr(spider, "name", None)
        try:
            bound["job_id"] = spider.crawler.settings.get("JOB")
        except Exception:
            pass
    bound.update({k: v for k, v in extra.items() if v is not None})
    return structlog.get_logger().bind(**bound) 