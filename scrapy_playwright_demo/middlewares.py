import random
import logging
from scrapy.exceptions import NotConfigured
from scrapy.utils.response import response_status_message
from scrapy_playwright_demo.config import app_settings
from scrapy_playwright_demo.utils.logging import get_logger

class RotatingUserAgentAndProxyMiddleware:
    def __init__(self, ua_list, proxy_url, retry_http_codes, retry_times):
        self.ua_list = ua_list
        self.proxy_url = proxy_url
        self.retry_http_codes = set(retry_http_codes)
        self.retry_times = retry_times
        self.logger = logging.getLogger(self.__class__.__name__)

    @classmethod
    def from_crawler(cls, crawler):
        # Prefer app_settings, fallback to Scrapy settings for compatibility
        ua_list = app_settings.rotating_ua_list or crawler.settings.getlist("ROTATING_UA_LIST")
        if not ua_list:
            raise NotConfigured("ROTATING_UA_LIST is not set or empty")
        proxy_url = app_settings.proxy_list[0] if app_settings.proxy_list else crawler.settings.get("PROXY_URL")
        retry_http_codes = app_settings.retry_http_codes or crawler.settings.getlist("RETRY_HTTP_CODES", [429, 503])
        retry_times = app_settings.retry_times or crawler.settings.getint("RETRY_TIMES", 5)
        mw = cls(ua_list, proxy_url, retry_http_codes, retry_times)
        return mw

    def process_request(self, request, spider):
        ua = random.choice(self.ua_list)
        request.headers["User-Agent"] = ua
        if self.proxy_url:
            request.meta["proxy"] = self.proxy_url
        logger = get_logger(spider)
        if logger.isEnabledFor("debug"):
            logger.debug(f"Using UA: {ua} | Proxy: {self.proxy_url}")

    def process_response(self, request, response, spider):
        logger = get_logger(spider)
        if response.status in self.retry_http_codes:
            retry_count = request.meta.get('retry_times', 0) + 1
            if retry_count > self.retry_times:
                msg = f"Gave up retrying {request} (failed {retry_count} times): {response_status_message(response.status)}"
                logger.warning(msg)
                return response
            # Exponential backoff: 1, 2, 4, 8, ... seconds
            delay = 2 ** (retry_count - 1)
            request.meta['download_delay'] = delay
            request.meta['retry_times'] = retry_count
            logger.info(f"Retrying {request} (status: {response.status}) | Backoff: {delay}s (retry {retry_count}/{self.retry_times})")
            return request.copy()
        return response 