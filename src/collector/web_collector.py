import logging
import re
from datetime import datetime, timezone, timedelta

import requests

from src.collector.base import BaseCollector
from src.config import REQUEST_TIMEOUT, USER_AGENT
from src.models import RawArticle

logger = logging.getLogger(__name__)


class Kr36Collector(BaseCollector):
    """36氪 AI 频道采集器"""

    name = "36氪"

    def fetch(self, since: datetime) -> list[RawArticle]:
        logger.info(f"[{self.name}] 开始采集")
        url = "https://36kr.com/api/newsflash"
        params = {"per_page": 50}
        try:
            resp = requests.get(
                url, params=params, timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": USER_AGENT},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"[{self.name}] 采集失败: {e}")
            return []

        articles = []
        items = data.get("data", {}).get("items", [])
        for item in items:
            pub_str = item.get("published_at", "")
            pub_time = self._parse_iso_time(pub_str)
            if pub_time and pub_time < since:
                continue

            title = item.get("title", "").strip()
            summary = item.get("description", "").strip()
            news_url = item.get("news_url", "") or item.get("url", "")
            if not news_url:
                news_id = item.get("id")
                if news_id:
                    news_url = f"https://36kr.com/newsflashes/{news_id}"
            if not title or not news_url:
                continue

            articles.append(RawArticle(
                title=title,
                summary=summary[:500],
                url=news_url,
                source=self.name,
                publish_time=pub_time or datetime.now(timezone.utc),
            ))

        logger.info(f"[{self.name}] 采集到 {len(articles)} 条文章")
        return articles

    @staticmethod
    def _parse_iso_time(time_str: str) -> datetime | None:
        if not time_str:
            return None
        try:
            time_str = time_str.replace("Z", "+00:00")
            return datetime.fromisoformat(time_str)
        except Exception:
            return None


class BaiduNewsCollector(BaseCollector):
    """百度资讯搜索采集器 — 搜索 AI 相关关键词，限定最近 1 天"""

    name = "百度资讯"

    SEARCH_QUERIES = ["AI大模型 最新", "人工智能应用 今日", "智能体Agent 最新", "AI芯片算力 今日"]

    def fetch(self, since: datetime) -> list[RawArticle]:
        logger.info(f"[{self.name}] 开始采集")
        all_articles = []
        for query in self.SEARCH_QUERIES:
            articles = self._search(query, since)
            all_articles.extend(articles)
        logger.info(f"[{self.name}] 采集到 {len(all_articles)} 条文章")
        return all_articles

    def _search(self, query: str, since: datetime) -> list[RawArticle]:
        now = datetime.now(timezone.utc)
        begin_ts = int(since.timestamp())
        end_ts = int(now.timestamp())

        url = "https://www.baidu.com/s"
        params = {
            "wd": query,
            "tn": "news",
            "rtt": "4",
            "bsst": "1",
            "cl": "2",
            "medium": "0",
            "gpc": f"stf={begin_ts},{end_ts}|stftype=2",
        }
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            html = resp.text
        except Exception as e:
            logger.error(f"[{self.name}] 搜索 '{query}' 失败: {e}")
            return []

        articles = []
        pattern = r'<h3[^>]*class="news-title[^"]*"[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
        matches = re.findall(pattern, html, re.DOTALL)
        for link, title_html in matches[:8]:
            title = re.sub(r"<[^>]+>", "", title_html).strip()
            if not title or not link:
                continue

            pub_time = self._extract_date_from_url(link)
            if pub_time and pub_time < since - timedelta(days=1):
                logger.info(f"[{self.name}] 跳过旧文章: {title[:30]}")
                continue

            articles.append(RawArticle(
                title=title,
                summary="",
                url=link,
                source=self.name,
                publish_time=pub_time or now,
            ))
        return articles

    @staticmethod
    def _extract_date_from_url(url: str) -> datetime | None:
        """尝试从 URL 中提取日期"""
        m = re.search(r'(20\d{2})[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])', url)
        if m:
            try:
                return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)
            except ValueError:
                pass
        return None
