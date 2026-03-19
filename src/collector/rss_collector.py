import logging
from datetime import datetime, timezone
from time import mktime

import feedparser
import requests

from src.collector.base import BaseCollector
from src.config import REQUEST_TIMEOUT, USER_AGENT
from src.models import RawArticle

logger = logging.getLogger(__name__)


class RSSCollector(BaseCollector):
    """通用 RSS 采集器"""

    def __init__(self, name: str, feed_url: str):
        self.name = name
        self.feed_url = feed_url

    def fetch(self, since: datetime) -> list[RawArticle]:
        logger.info(f"[{self.name}] 开始采集 RSS: {self.feed_url}")
        try:
            resp = requests.get(
                self.feed_url, timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, text/xml"},
            )
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except Exception as e:
            logger.error(f"[{self.name}] RSS 采集失败: {e}")
            return []

        articles = []
        for entry in feed.entries:
            pub_time = self._parse_time(entry)
            if pub_time and pub_time < since:
                continue

            summary = ""
            if hasattr(entry, "summary"):
                summary = self._clean_html(entry.summary)
            elif hasattr(entry, "description"):
                summary = self._clean_html(entry.description)

            link = entry.get("link", "")
            if not link:
                continue

            articles.append(RawArticle(
                title=entry.get("title", "").strip(),
                summary=summary[:500],
                url=link.strip(),
                source=self.name,
                publish_time=pub_time or datetime.now(timezone.utc),
            ))

        logger.info(f"[{self.name}] 采集到 {len(articles)} 条文章")
        return articles

    @staticmethod
    def _parse_time(entry) -> datetime | None:
        for attr in ("published_parsed", "updated_parsed"):
            parsed = getattr(entry, attr, None)
            if parsed:
                try:
                    return datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
                except Exception:
                    pass
        return None

    @staticmethod
    def _clean_html(text: str) -> str:
        import re
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
