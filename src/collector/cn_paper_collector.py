"""中文 AI 论文/研究解读采集器 — 从专业科技媒体采集论文解读与前沿研究"""
import logging
import re
from datetime import datetime, timezone
from time import mktime

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
    "site:jiqizhixin.com 论文",
    "site:qbitai.com 论文",
    "site:jiqizhixin.com 研究",
    "site:qbitai.com 研究",
    "AI论文解读 最新 2026",
    "大模型 论文 arXiv",
    "人工智能 研究突破 论文",
    "深度学习 论文速递",
]

PAPER_STRONG_SIGNALS = [
    "论文", "paper", "arxiv", "论文解读", "论文速递", "论文推荐",
    "论文精读", "论文导读", "技术报告",
]

PAPER_RESEARCH_SIGNALS = [
    "研究", "提出", "模型", "方法", "算法", "架构", "框架",
    "实验", "数据集", "benchmark", "评测", "sota",
    "开源", "突破", "发现", "证明", "表明",
    "训练", "推理", "微调", "预训练", "fine-tune",
    "attention", "transformer", "diffusion", "moe",
    "参数", "性能", "准确率", "效果",
]

AI_MUST_KEYWORDS = [
    "ai", "人工智能", "大模型", "深度学习", "机器学习",
    "transformer", "gpt", "llm", "bert", "diffusion",
    "多模态", "智能体", "agent", "具身智能",
    "算力", "神经网络", "自然语言处理", "nlp",
    "计算机视觉", "cv", "语音识别", "aigc", "生成式",
    "rag", "强化学习", "机器人", "moe",
    "视觉语言", "世界模型", "reasoning", "推理",
]

PAPER_NEGATIVE_KEYWORDS = [
    "医疗", "医学", "药物", "临床", "患者", "癌症", "肿瘤",
    "心脏", "血液", "细胞", "基因", "蛋白", "手术",
    "牙周", "抑郁", "焦虑", "阿尔茨海默",
    "股票", "分红", "股本", "涨停", "跌停", "基金",
    "利润", "营收", "财报", "净利", "毛利", "市值蒸发",
    "足球", "篮球", "体育", "奥运",
    "房地产", "楼市", "房价",
    "娱乐", "综艺", "选秀", "明星",
]

NEWS_ONLY_REJECT = [
    "售价", "优惠", "获得融资", "完成融资", "获投",
    "股价", "涨幅", "跌幅", "市值",
]


class CnPaperCollector(BaseCollector):
    """采集 AI 论文解读与前沿研究类中文文章"""

    name = "论文解读"

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
            title_key = re.sub(r"[\s\W]+", "", p.title)[:20]
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            unique.append(p)

        unique.sort(key=lambda p: self._paper_score(p), reverse=True)
        logger.info(f"[{self.name}] 去重后共 {len(unique)} 篇")
        return unique

    def _fetch_from_rss(self, since: datetime) -> list[RawArticle]:
        results = []
        for name, feed_url in PAPER_RSS_FEEDS.items():
            try:
                resp = requests.get(
                    feed_url, timeout=REQUEST_TIMEOUT,
                    headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, text/xml"},
                )
                resp.raise_for_status()
                feed = feedparser.parse(resp.content)
                if not feed.entries:
                    logger.warning(f"[{self.name}] RSS {name} 无条目")
                    continue

                count = 0
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

                    if not self._is_rss_paper(title, summary):
                        continue

                    results.append(RawArticle(
                        title=title,
                        summary=summary[:500],
                        url=link,
                        source=name,
                        publish_time=pub_time or datetime.now(timezone.utc),
                    ))
                    count += 1

                logger.info(f"[{self.name}] RSS {name}: {count} 篇研究相关")
            except Exception as e:
                logger.warning(f"[{self.name}] RSS {name} 采集失败: {e}")
        return results

    def _fetch_from_search(self, since: datetime) -> list[RawArticle]:
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

        logger.info(f"[{self.name}] 搜索总计 {len(all_results)} 篇")
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
            r'<h3[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            r'href="(https?://[^"]+)"[^>]*>([\u4e00-\u9fff][\s\S]*?)</a>',
        ]
        all_matches = []
        for pat in patterns:
            found = re.findall(pat, html, re.DOTALL)
            if found:
                all_matches = found
                break

        for link, title_html in all_matches[:10]:
            title = re.sub(r"<[^>]+>", "", title_html).strip()
            title = re.sub(r"\s+", " ", title)
            if not title or not link or len(title) < 6:
                continue
            if "百度" in title and "搜索" in title:
                continue

            if not self._is_search_paper(title):
                continue

            pub_time = self._extract_date_from_url(link)
            papers.append(RawArticle(
                title=title,
                summary="",
                url=link,
                source="论文搜索",
                publish_time=pub_time or now,
            ))

        return papers

    @classmethod
    def _is_rss_paper(cls, title: str, summary: str) -> bool:
        """RSS 来源过滤（机器之心/量子位本身就是AI媒体，适度放宽）"""
        text = f"{title} {summary}".lower()

        if any(neg in text for neg in PAPER_NEGATIVE_KEYWORDS):
            return False

        title_lower = title.lower()
        if any(kw in title_lower for kw in NEWS_ONLY_REJECT):
            return False

        has_ai = any(kw in text for kw in AI_MUST_KEYWORDS)
        if not has_ai:
            return False

        has_strong = any(kw in text for kw in PAPER_STRONG_SIGNALS)
        if has_strong:
            return True

        research_hits = sum(1 for kw in PAPER_RESEARCH_SIGNALS if kw in text)
        return research_hits >= 2

    @classmethod
    def _is_search_paper(cls, title: str) -> bool:
        """搜索结果过滤（较严格，标题须有论文/研究信号）"""
        text = title.lower()

        if any(neg in text for neg in PAPER_NEGATIVE_KEYWORDS):
            return False
        if any(kw in text for kw in NEWS_ONLY_REJECT):
            return False

        has_ai = any(kw in text for kw in AI_MUST_KEYWORDS)
        if not has_ai:
            return False

        has_strong = any(kw in text for kw in PAPER_STRONG_SIGNALS)
        has_research = any(kw in text for kw in PAPER_RESEARCH_SIGNALS)
        return has_strong or has_research

    @staticmethod
    def _paper_score(article: RawArticle) -> float:
        """论文相关度排序打分"""
        text = f"{article.title} {article.summary}".lower()
        score = 0.0
        for kw in PAPER_STRONG_SIGNALS:
            if kw in text:
                score += 3
        for kw in PAPER_RESEARCH_SIGNALS:
            if kw in text:
                score += 1
        if article.source in ("机器之心", "量子位"):
            score += 2
        return score

    @staticmethod
    def _parse_rss_time(entry) -> datetime | None:
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
