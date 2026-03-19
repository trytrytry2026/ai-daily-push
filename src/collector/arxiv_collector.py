"""arXiv 论文采集器 — 采集最近 AI 方向论文"""
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

import requests

from src.collector.base import BaseCollector
from src.config import REQUEST_TIMEOUT, USER_AGENT
from src.models import RawArticle

logger = logging.getLogger(__name__)

ARXIV_API = "http://export.arxiv.org/api/query"

ARXIV_CATEGORIES = ["cs.AI", "cs.CL", "cs.LG", "cs.CV", "cs.MA"]

ARXIV_SEARCH_QUERIES = [
    "large language model",
    "AI agent",
    "multimodal",
    "reasoning",
    "reinforcement learning from human feedback",
]

NS = {"atom": "http://www.w3.org/2005/Atom"}


class ArxivCollector(BaseCollector):
    """arXiv 论文采集"""

    name = "arXiv"

    def fetch(self, since: datetime) -> list[RawArticle]:
        logger.info(f"[{self.name}] 开始采集论文")
        all_papers = []

        for query in ARXIV_SEARCH_QUERIES:
            papers = self._search(query, max_results=10)
            all_papers.extend(papers)

        seen_ids = set()
        unique = []
        for p in all_papers:
            paper_id = re.sub(r"v\d+$", "", p.url.split("/abs/")[-1])
            if paper_id not in seen_ids:
                seen_ids.add(paper_id)
                unique.append(p)

        logger.info(f"[{self.name}] 采集到 {len(unique)} 篇去重后的论文")
        return unique

    def _search(self, query: str, max_results: int = 10) -> list[RawArticle]:
        cat_filter = " OR ".join(f"cat:{c}" for c in ARXIV_CATEGORIES)
        full_query = f"all:{query} AND ({cat_filter})"

        params = {
            "search_query": full_query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        try:
            resp = requests.get(
                ARXIV_API, params=params,
                timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": USER_AGENT},
            )
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"[{self.name}] 搜索 '{query}' 失败: {e}")
            return []

        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError as e:
            logger.error(f"[{self.name}] XML 解析失败: {e}")
            return []

        papers = []
        for entry in root.findall("atom:entry", NS):
            title = entry.findtext("atom:title", "", NS).strip()
            title = re.sub(r"\s+", " ", title)
            summary = entry.findtext("atom:summary", "", NS).strip()
            summary = re.sub(r"\s+", " ", summary)[:500]

            link_el = entry.find("atom:id", NS)
            url = link_el.text.strip() if link_el is not None else ""

            published = entry.findtext("atom:published", "", NS)
            pub_time = self._parse_time(published)

            if not title or not url:
                continue

            papers.append(RawArticle(
                title=title,
                summary=summary,
                url=url,
                source=self.name,
                publish_time=pub_time or datetime.now(timezone.utc),
            ))

        return papers

    @staticmethod
    def _parse_time(time_str: str) -> datetime | None:
        if not time_str:
            return None
        try:
            return datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        except Exception:
            return None
