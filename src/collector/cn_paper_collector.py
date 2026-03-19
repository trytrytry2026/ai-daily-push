"""中文 AI 论文/研究采集器 — 多源采集国内科技媒体的论文解读"""
import logging
import re
from datetime import datetime, timezone, timedelta

import feedparser
import requests

from src.collector.base import BaseCollector
from src.config import REQUEST_TIMEOUT, USER_AGENT
from src.models import RawArticle

logger = logging.getLogger(__name__)


PAPER_RSS_FEEDS = {
    "机器之心": "https://www.jiqizhixin.com/rss",
    "量子位": "https://www.qbitai.com/feed",
}

PAPER_SEARCH_QUERIES = [
    "AI论文解读",
    "大模型最新研究",
    "人工智能研究突破",
    "深度学习最新论文",
    "AI技术论文",
    "大模型论文",
    "智能体研究",
    "多模态模型研究",
]

PAPER_KEYWORDS = [
    "论文", "研究", "模型", "算法", "架构", "框架",
    "突破", "提出", "方法", "技术", "开源",
    "AI", "人工智能", "大模型", "深度学习", "机器学习",
    "神经网络", "transformer", "gpt", "llm",
    "多模态", "扩散", "生成", "推理", "训练",
    "智能体", "agent", "具身智能", "数据集",
]


class CnPaperCollector(BaseCollector):
    """多源中文 AI 论文/研究采集器"""

    name = "中文论文"

    def fetch(self, since: datetime) -> list[RawArticle]:
        logger.info(f"[{self.name}] 开始采集，时间范围: {since.date()} 至今")
        all_papers = []

        rss_papers = self._fetch_from_rss(since)
        all_papers.extend(rss_papers)
        logger.info(f"[{self.name}] RSS 采集到 {len(rss_papers)} 篇")

        search_papers = self._fetch_from_search(since)
        all_papers.extend(search_papers)
        logger.info(f"[{self.name}] 搜索采集到 {len(search_papers)} 篇")

        seen_titles = set()
        unique = []
        for p in all_papers:
            title_key = re.sub(r"[\s\W]+", "", p.title)[:25]
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            unique.append(p)

        unique.sort(key=lambda p: p.publish_time, reverse=True)
        logger.info(f"[{self.name}] 去重后共 {len(unique)} 篇")
        return unique

    def _fetch_from_rss(self, since: datetime) -> list[RawArticle]:
        """从 RSS 源采集论文/研究相关文章"""
        results = []
        for name, feed_url in PAPER_RSS_FEEDS.items():
            try:
                feed = feedparser.parse(
                    feed_url, agent=USER_AGENT,
                    request_headers={"Accept": "application/rss+xml, application/xml, text/xml"},
                )
                for entry in feed.entries:
                    pub_time = self._parse_rss_time(entry)
                    if pub_time and pub_time < since:
                        continue

                    title = entry.get("title", "").strip()
                    summary = ""
                    if hasattr(entry, "summary"):
                        summary = re.sub(r"<[^>]+>", "", entry.summary).strip()
                    elif hasattr(entry, "description"):
                        summary = re.sub(r"<[^>]+>", "", entry.description).strip()

                    link = entry.get("link", "")
                    if not title or not link:
                        continue

                    text = f"{title} {summary}".lower()
                    if not any(kw in text for kw in PAPER_KEYWORDS):
                        continue

                    results.append(RawArticle(
                        title=title,
                        summary=summary[:500],
                        url=link,
                        source=name,
                        publish_time=pub_time or datetime.now(timezone.utc),
                    ))
            except Exception as e:
                logger.warning(f"[{self.name}] RSS {name} 采集失败: {e}")
        return results

    def _fetch_from_search(self, since: datetime) -> list[RawArticle]:
        """从百度搜索采集论文相关文章"""
        all_results = []
        now = datetime.now(timezone.utc)
        begin_ts = int(since.timestamp())
        end_ts = int(now.timestamp())

        for query in PAPER_SEARCH_QUERIES:
            try:
                papers = self._search_one(query, begin_ts, end_ts, now)
                all_results.extend(papers)
            except Exception as e:
                logger.warning(f"[{self.name}] 搜索 '{query}' 异常: {e}")

        return all_results

    def _search_one(self, query: str, begin_ts: int, end_ts: int, now: datetime) -> list[RawArticle]:
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
        resp = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        html = resp.text

        papers = []
        patterns = [
            r'<h3[^>]*class="news-title[^"]*"[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            r'<h3[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*data-click[^>]*>(.*?)</a>',
            r'<a[^>]*href="(https?://[^"]+)"[^>]*class="[^"]*news[^"]*"[^>]*>(.*?)</a>',
        ]

        matches = []
        for pat in patterns:
            found = re.findall(pat, html, re.DOTALL)
            matches.extend(found)
            if found:
                break

        for link, title_html in matches[:8]:
            title = re.sub(r"<[^>]+>", "", title_html).strip()
            if not title or not link or len(title) < 8:
                continue

            pub_time = self._extract_date_from_url(link)

            papers.append(RawArticle(
                title=title,
                summary="",
                url=link,
                source="百度学术",
                publish_time=pub_time or now,
            ))

        return papers

    @staticmethod
    def _parse_rss_time(entry) -> datetime | None:
        from time import mktime
        for attr in ("published_parsed", "updated_parsed"):
            parsed = getattr(entry, attr, None)
            if parsed:
                try:
                    return datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
                except Exception:
                    pass
        return None

    @staticmethod
    def _extract_date_from_url(url: str) -> datetime | None:
        m = re.search(r'(20\d{2})[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])', url)
        if m:
            try:
                return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)
            except ValueError:
                pass
        return None
