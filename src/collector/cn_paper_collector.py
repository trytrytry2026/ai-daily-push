"""中文 AI 论文/研究解读采集器 — 多引擎搜索 + RSS + 多级容错"""
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

BING_QUERIES = [
    "AI 论文解读 site:jiqizhixin.com",
    "论文 site:qbitai.com",
    "AI论文解读 2026",
    "大模型 论文解读 最新",
    "深度学习 论文速递 中文",
    "arXiv 论文 中文解读",
    "AI论文精读 推荐",
    "人工智能 研究 论文 突破",
    "LLM 论文解读",
    "多模态 论文 研究",
]

BAIDU_QUERIES = [
    "AI 论文解读",
    "大模型 论文解读",
    "深度学习 最新论文",
    "AI 论文速递",
    "人工智能 论文推荐",
    "arXiv 论文 中文解读",
    "机器学习 论文 研究",
    "LLM 论文 最新",
]

GOOGLE_QUERIES = [
    "AI 论文解读 site:jiqizhixin.com",
    "AI 论文解读 site:qbitai.com",
    "大模型 论文解读 中文",
    "深度学习 论文速递",
]

PAPER_STRONG_SIGNALS = [
    "论文", "paper", "arxiv", "论文解读", "论文速递", "论文推荐",
    "论文精读", "论文导读", "研究论文",
]

PAPER_WEAK_SIGNALS = [
    "研究发现", "研究表明", "研究证实", "实验表明", "实验证明",
    "研究团队", "研究人员", "研究者", "技术报告",
    "提出了", "证明了", "刷新", "benchmark", "sota",
    "开源模型", "模型架构", "训练方法",
]

AI_KEYWORDS = [
    "ai", "人工智能", "大模型", "深度学习", "机器学习",
    "transformer", "gpt", "llm", "bert", "diffusion",
    "多模态", "智能体", "agent", "具身智能",
    "神经网络", "自然语言处理", "nlp",
    "计算机视觉", "语音识别", "aigc", "生成式",
    "rag", "强化学习", "moe", "reasoning",
    "视觉语言", "世界模型", "模型", "算法",
]

NEGATIVE_KEYWORDS = [
    "股票", "涨停", "跌停", "基金", "财报", "市值",
    "足球", "篮球", "体育",
    "房地产", "楼市", "房价",
    "娱乐", "综艺", "选秀", "明星",
    "售价", "优惠", "获投", "股价", "融资",
    "招聘", "薪资", "简历",
]


class CnPaperCollector(BaseCollector):
    """采集 AI 论文解读类中文文章，多级过滤 + 容错"""

    name = "论文解读"

    def fetch(self, since: datetime) -> list[RawArticle]:
        logger.info(f"[{self.name}] 开始采集，时间范围: {since.date()} 至今")
        all_papers: list[RawArticle] = []

        for method_name, fetcher in [
            ("RSS", lambda: self._fetch_from_rss(since)),
            ("Bing", lambda: self._fetch_from_bing(since)),
            ("Baidu", lambda: self._fetch_from_baidu(since)),
            ("Google", lambda: self._fetch_from_google(since)),
        ]:
            try:
                results = fetcher()
                all_papers.extend(results)
                logger.info(f"[{self.name}] {method_name} 采集到 {len(results)} 篇")
            except Exception as e:
                logger.warning(f"[{self.name}] {method_name} 采集失败: {e}")

        unique = self._dedup(all_papers)
        logger.info(f"[{self.name}] 去重后共 {len(unique)} 篇")

        strict = [p for p in unique if self._is_paper_strict(p)]
        logger.info(f"[{self.name}] 严格过滤后 {len(strict)} 篇")

        if len(strict) >= 5:
            strict.sort(key=self._paper_score, reverse=True)
            return strict

        relaxed = [p for p in unique if self._is_paper_relaxed(p)]
        logger.info(f"[{self.name}] 宽松过滤后 {len(relaxed)} 篇")
        relaxed.sort(key=self._paper_score, reverse=True)
        return relaxed

    def _dedup(self, papers: list[RawArticle]) -> list[RawArticle]:
        seen = set()
        unique = []
        for p in papers:
            key = re.sub(r"[\s\W]+", "", p.title)[:20]
            if key in seen:
                continue
            seen.add(key)
            unique.append(p)
        return unique

    # ── RSS ──────────────────────────────────────────

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

                    text = f"{title} {summary}".lower()
                    if any(neg in text for neg in NEGATIVE_KEYWORDS):
                        continue

                    results.append(RawArticle(
                        title=title, summary=summary[:500], url=link,
                        source=name, publish_time=pub_time or datetime.now(timezone.utc),
                    ))
                    count += 1

                logger.info(f"[{self.name}] RSS {name}: 共 {count} 篇")
            except Exception as e:
                logger.warning(f"[{self.name}] RSS {name} 采集失败: {e}")
        return results

    # ── Bing 搜索 ──────────────────────────────────

    def _fetch_from_bing(self, since: datetime) -> list[RawArticle]:
        all_results = []
        now = datetime.now(timezone.utc)
        for query in BING_QUERIES:
            try:
                papers = self._search_bing(query, now, since)
                all_results.extend(papers)
            except Exception as e:
                logger.warning(f"[{self.name}] Bing '{query}' 异常: {e}")
        return all_results

    def _search_bing(self, query: str, now: datetime, since: datetime) -> list[RawArticle]:
        url = "https://www.bing.com/search"
        params = {"q": query, "setlang": "zh-Hans", "cc": "CN", "filters": "ex1:\"ez1\""}
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        resp = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        html = resp.text

        papers = []
        matches = re.findall(r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
        for link, title_html in matches:
            title = re.sub(r"<[^>]+>", "", title_html).strip()
            title = re.sub(r"\s+", " ", title)
            if not title or len(title) < 8:
                continue
            if any(s in link for s in ["bing.com", "microsoft.com", "go.microsoft", "login"]):
                continue
            text = title.lower()
            if any(neg in text for neg in NEGATIVE_KEYWORDS):
                continue

            pub_time = self._extract_date_from_url(link)
            if pub_time and pub_time < since:
                continue

            papers.append(RawArticle(
                title=title, summary="", url=link,
                source="Bing搜索", publish_time=pub_time or now,
            ))
        return papers[:6]

    # ── Google 搜索 ──────────────────────────────────

    def _fetch_from_google(self, since: datetime) -> list[RawArticle]:
        all_results = []
        now = datetime.now(timezone.utc)
        for query in GOOGLE_QUERIES:
            try:
                papers = self._search_google(query, now, since)
                all_results.extend(papers)
            except Exception as e:
                logger.warning(f"[{self.name}] Google '{query}' 异常: {e}")
        return all_results

    def _search_google(self, query: str, now: datetime, since: datetime) -> list[RawArticle]:
        url = "https://www.google.com/search"
        params = {"q": query, "hl": "zh-CN", "tbs": "qdr:w", "num": "10"}
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        resp = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        html = resp.text

        papers = []
        matches = re.findall(r'<a[^>]*href="/url\?q=(https?://[^&"]+)[^"]*"[^>]*>(.*?)</a>', html, re.DOTALL)
        if not matches:
            matches = re.findall(r'<a[^>]*href="(https?://(?:www\.)?(?:jiqizhixin|qbitai|paperweekly)[^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)

        for link, title_html in matches:
            title = re.sub(r"<[^>]+>", "", title_html).strip()
            title = re.sub(r"\s+", " ", title)
            if not title or len(title) < 8:
                continue
            if any(s in link for s in ["google.com", "youtube.com", "accounts.google"]):
                continue
            text = title.lower()
            if any(neg in text for neg in NEGATIVE_KEYWORDS):
                continue
            pub_time = self._extract_date_from_url(link)
            if pub_time and pub_time < since:
                continue

            papers.append(RawArticle(
                title=title, summary="", url=link,
                source="Google搜索", publish_time=pub_time or now,
            ))
        return papers[:6]

    # ── 百度搜索 ──────────────────────────────────

    def _fetch_from_baidu(self, since: datetime) -> list[RawArticle]:
        all_results = []
        now = datetime.now(timezone.utc)
        begin_ts = int(since.timestamp())
        end_ts = int(now.timestamp())
        for query in BAIDU_QUERIES:
            try:
                papers = self._search_baidu(query, begin_ts, end_ts, now)
                all_results.extend(papers)
            except Exception as e:
                logger.warning(f"[{self.name}] 百度 '{query}' 异常: {e}")
        return all_results

    def _search_baidu(self, query: str, begin_ts: int, end_ts: int, now: datetime) -> list[RawArticle]:
        url = "https://www.baidu.com/s"
        params = {
            "wd": query, "tn": "news", "rtt": "4", "bsst": "1",
            "cl": "2", "medium": "0",
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
        for pat in [r'<h3[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                     r'href="(https?://[^"]+)"[^>]*>([\u4e00-\u9fff][\s\S]*?)</a>']:
            found = re.findall(pat, html, re.DOTALL)
            if found:
                for link, title_html in found[:10]:
                    title = re.sub(r"<[^>]+>", "", title_html).strip()
                    title = re.sub(r"\s+", " ", title)
                    if not title or not link or len(title) < 6:
                        continue
                    if "百度" in title and "搜索" in title:
                        continue
                    text = title.lower()
                    if any(neg in text for neg in NEGATIVE_KEYWORDS):
                        continue
                    pub_time = self._extract_date_from_url(link)
                    papers.append(RawArticle(
                        title=title, summary="", url=link,
                        source="论文搜索", publish_time=pub_time or now,
                    ))
                break
        return papers

    # ── 过滤策略 ────────────────────────────────

    @staticmethod
    def _is_paper_strict(article: RawArticle) -> bool:
        """严格：必须有强论文信号词"""
        text = f"{article.title} {article.summary}".lower()
        return any(kw in text for kw in PAPER_STRONG_SIGNALS)

    @staticmethod
    def _is_paper_relaxed(article: RawArticle) -> bool:
        """宽松：有弱论文信号词 或 来自可信来源 且 含AI词"""
        text = f"{article.title} {article.summary}".lower()
        if any(kw in text for kw in PAPER_STRONG_SIGNALS):
            return True
        if any(kw in text for kw in PAPER_WEAK_SIGNALS):
            return True
        if article.source in ("机器之心", "量子位") and any(kw in text for kw in AI_KEYWORDS):
            return True
        return False

    @staticmethod
    def _paper_score(article: RawArticle) -> float:
        text = f"{article.title} {article.summary}".lower()
        score = sum(5 for kw in PAPER_STRONG_SIGNALS if kw in text)
        score += sum(2 for kw in PAPER_WEAK_SIGNALS if kw in text)
        if article.source in ("机器之心", "量子位"):
            score += 8
        if article.source in ("Bing搜索", "Google搜索"):
            score += 2
        return score

    # ── 工具方法 ──────────────────────────────────

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
