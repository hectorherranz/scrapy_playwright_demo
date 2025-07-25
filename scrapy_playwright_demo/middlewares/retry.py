from scrapy_playwright_demo.retry import build_retry_policy
from scrapy_playwright_demo.utils.logging import get_logger
from twisted.internet import reactor, defer
from scrapy.utils.response import response_status_message
from scrapy.exceptions import IgnoreRequest

class CustomRetryMiddleware:
    def __init__(self, policy):
        self.policy = policy

    @classmethod
    def from_crawler(cls, crawler):
        container = crawler.settings.get("CONTAINER")
        if container is None:
            raise RuntimeError("DI Container not found in settings. Make sure settings.CONTAINER is set.")
        policy = container.retry_policy()
        return cls(policy)

    def process_response(self, request, response, spider):
        logger = get_logger(spider)
        attempt = request.meta.get("retry_attempt", 0)
        if response.status in self.policy.retry_http_codes:
            if attempt < self.policy.max_retries:
                delay = self.policy.next_delay(attempt)
                logger.info("retrying_response", url=request.url, status=response.status, attempt=attempt+1, delay=delay)
                new_request = request.copy()
                new_request.meta["retry_attempt"] = attempt + 1
                new_request.meta["download_delay"] = delay
                new_request.dont_filter = True
                return new_request
            else:
                logger.warning("max_retries_exceeded", url=request.url, status=response.status)
                raise IgnoreRequest(f"Gave up retrying {request} (failed {attempt} times): {response_status_message(response.status)}")
        return response

    def process_exception(self, request, exception, spider):
        logger = get_logger(spider)
        attempt = request.meta.get("retry_attempt", 0)
        if isinstance(exception, self.policy.retry_exceptions):
            if attempt < self.policy.max_retries:
                delay = self.policy.next_delay(attempt)
                logger.info("retrying_exception", url=request.url, exc=type(exception).__name__, attempt=attempt+1, delay=delay)
                new_request = request.copy()
                new_request.meta["retry_attempt"] = attempt + 1
                new_request.meta["download_delay"] = delay
                new_request.dont_filter = True
                return new_request
            else:
                logger.warning("max_retries_exceeded_exception", url=request.url, exc=type(exception).__name__)
                raise IgnoreRequest(f"Gave up retrying {request} (failed {attempt} times): {exception}")
        return None 