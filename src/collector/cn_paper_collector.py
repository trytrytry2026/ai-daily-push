"""中文 AI 论文采集器 — 从国内科技媒体采集论文解读/推荐"""
import logging
import re
from datetime import datetime, timezone, timedelta

import requests

from src.collector.base import BaseCollector
from src.config import REQUEST_TIMEOUT, USER_AGENT
from src.models import RawArticle

logger = logging.getLogger(__name__)


PAPER_SEARCH_QUERIES = [
    "AI论文 解读",
    "大模型 最新论文",
    "人工智能 研究突破",
    "深度学习 论文推荐",
    "机器学习 最新研究",
]

TRUSTED_DOMAINS = [
    "jiqizhixin.com",
    "qbitai.com",
    "paperweekly",
    "thepaper.cn",
    "36kr.com",
    "ithome.com",
    "csdn.net",
    "zhihu.com",
    "baidu.com/link",
    "baijiahao.baidu.com",
    "mp.weixin.qq.com",
    "sohu.com",
    "163.com",
    "sina.com",
    "xinhuanet.com",
]


class CnPaperCollector(BaseCollector):
    """从百度搜索采集中文 AI 论文解读文章"""

    name = "中文论文"

    def fetch(self, since: datetime) -> list[RawArticle]:
        logger.info(f"[{self.name}] 开始采集中文论文解读")
        all_papers = []

        for query in PAPER_SEARCH_QUERIES:
            papers = self._search_baidu(query, since)
            all_papers.extend(papers)

        seen_urls = set()
        seen_titles = set()
        unique = []
        for p in all_papers:
            url_key = re.sub(r"[?#].*$", "", p.url)
            title_key = re.sub(r"\s+", "", p.title)[:20]
            if url_key in seen_urls or title_key in seen_titles:
                continue
            seen_urls.add(url_key)
            seen_titles.add(title_key)
            unique.append(p)

        logger.info(f"[{self.name}] 采集到 {len(unique)} 篇去重后的论文解读")
        return unique

    def _search_baidu(self, query: str, since: datetime) -> list[RawArticle]:
        now = datetime.now(timezone.utc)
        begin_ts = int(since.timestamp())
        end_ts = int(now.timestamp())

        url = "https://www.baidu.com/s"
        params = {
            "wd": f"{query} 论文",
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

        papers = []
        pattern = r'<h3[^>]*class="news-title[^"]*"[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
        matches = re.findall(pattern, html, re.DOTALL)

        for link, title_html in matches[:6]:
            title = re.sub(r"<[^>]+>", "", title_html).strip()
            if not title or not link:
                continue
            if not self._is_paper_related(title):
                continue

            pub_time = self._extract_date_from_url(link)
            if pub_time and pub_time < since:
                continue

            papers.append(RawArticle(
                title=title,
                summary="",
                url=link,
                source=self.name,
                publish_time=pub_time or now,
            ))

        return papers

    @staticmethod
    def _is_paper_related(title: str) -> bool:
        paper_kw = [
            "论文", "研究", "模型", "算法", "架构", "框架",
            "突破", "发现", "提出", "实现", "方法",
            "AI", "人工智能", "大模型", "深度学习", "机器学习",
            "神经网络", "Transformer", "GPT", "LLM",
            "多模态", "扩散", "生成", "推理", "训练",
        ]
        return any(kw.lower() in title.lower() for kw in paper_kw)

    @staticmethod
    def _extract_date_from_url(url: str) -> datetime | None:
        m = re.search(r'(20\d{2})[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])', url)
        if m:
            try:
                return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)
            except ValueError:
                pass
        return None
