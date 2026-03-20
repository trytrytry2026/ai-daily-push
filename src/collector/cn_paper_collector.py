"""中文 AI 论文/研究解读采集器 — 多引擎搜索 + RSS，严格只保留论文/研究类"""
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

BAIDU_QUERIES = [
    "AI 论文解读",
    "大模型 论文 解读",
    "人工智能 论文 arXiv",
    "深度学习 论文速递",
    "AI 论文推荐",
    "大模型 研究 论文",
]

BING_QUERIES = [
    "AI 论文解读 site:jiqizhixin.com",
    "论文 site:qbitai.com",
    "AI论文解读 最新",
    "大模型 论文 arXiv 解读",
    "深度学习 论文推荐",
    "人工智能 研究论文",
]

PAPER_SIGNALS = [
    "论文", "paper", "arxiv", "论文解读", "论文速递", "论文推荐",
    "论文精读", "论文导读", "技术报告", "研究发现", "研究表明",
    "研究证实", "研究团队", "实验证明", "实验表明", "实验结果",
    "提出了", "我们提出", "研究人员", "研究者",
    "数据集", "benchmark", "评测", "开源模型", "开源框架",
    "预训练", "微调", "fine-tune", "训练方法",
    "模型架构", "注意力机制", "attention",
    "sota", "state-of-the-art", "性能提升", "准确率",
]

AI_KEYWORDS = [
    "ai", "人工智能", "大模型", "深度学习", "机器学习",
    "transformer", "gpt", "llm", "bert", "diffusion",
    "多模态", "智能体", "agent", "具身智能",
    "神经网络", "自然语言处理", "nlp",
    "计算机视觉", "语音识别", "aigc", "生成式",
    "rag", "强化学习", "moe",
    "视觉语言", "世界模型",
]

NEGATIVE_KEYWORDS = [
    "医疗", "医学", "药物", "临床", "患者", "癌症", "肿瘤",
    "基因", "蛋白", "手术",
    "股票", "涨停", "跌停", "基金", "财报", "市值",
    "足球", "篮球", "体育",
    "房地产", "楼市", "房价",
    "娱乐", "综艺", "选秀", "明星",
    "售价", "优惠", "获投", "股价", "融资",
    "发布会", "新品发布", "上市",
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

        bing_papers = self._fetch_from_bing()
        all_papers.extend(bing_papers)
        logger.info(f"[{self.name}] Bing 搜索采集到 {len(bing_papers)} 篇")

        baidu_papers = self._fetch_from_baidu(since)
        all_papers.extend(baidu_papers)
        logger.info(f"[{self.name}] 百度搜索采集到 {len(baidu_papers)} 篇")

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

                    text = f"{title} {summary}".lower()
                    if not self._is_paper(text):
                        continue

                    results.append(RawArticle(
                        title=title,
                        summary=summary[:500],
                        url=link,
                        source=name,
                        publish_time=pub_time or datetime.now(timezone.utc),
                    ))
                    count += 1

                logger.info(f"[{self.name}] RSS {name}: {count} 篇")
            except Exception as e:
                logger.warning(f"[{self.name}] RSS {name} 采集失败: {e}")
        return results

    def _fetch_from_bing(self) -> list[RawArticle]:
        all_results = []
        now = datetime.now(timezone.utc)

        for query in BING_QUERIES:
            try:
                papers = self._search_bing(query, now)
                all_results.extend(papers)
            except Exception as e:
                logger.warning(f"[{self.name}] Bing '{query}' 异常: {e}")

        return all_results

    def _search_bing(self, query: str, now: datetime) -> list[RawArticle]:
        url = "https://www.bing.com/search"
        params = {"q": query, "setlang": "zh-Hans", "cc": "CN"}
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
            if any(skip in link for skip in ["bing.com", "microsoft.com", "go.microsoft", "login"]):
                continue

            if not self._is_paper(title.lower()):
                continue

            pub_time = self._extract_date_from_url(link)
            papers.append(RawArticle(
                title=title, summary="", url=link,
                source="Bing搜索",
                publish_time=pub_time or now,
            ))

        return papers[:8]

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
        for pat in [
            r'<h3[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            r'href="(https?://[^"]+)"[^>]*>([\u4e00-\u9fff][\s\S]*?)</a>',
        ]:
            found = re.findall(pat, html, re.DOTALL)
            if found:
                for link, title_html in found[:10]:
                    title = re.sub(r"<[^>]+>", "", title_html).strip()
                    title = re.sub(r"\s+", " ", title)
                    if not title or not link or len(title) < 6:
                        continue
                    if "百度" in title and "搜索" in title:
                        continue
                    if not self._is_paper(title.lower()):
                        continue

                    pub_time = self._extract_date_from_url(link)
                    papers.append(RawArticle(
                        title=title, summary="", url=link,
                        source="论文搜索",
                        publish_time=pub_time or now,
                    ))
                break

        return papers

    @staticmethod
    def _is_paper(text: str) -> bool:
        """必须同时满足：无负面词 + 有AI词 + 有论文/研究信号"""
        if any(neg in text for neg in NEGATIVE_KEYWORDS):
            return False
        has_ai = any(kw in text for kw in AI_KEYWORDS)
        has_paper = any(kw in text for kw in PAPER_SIGNALS)
        return has_ai and has_paper

    @staticmethod
    def _paper_score(article: RawArticle) -> float:
        text = f"{article.title} {article.summary}".lower()
        score = sum(3 for kw in PAPER_SIGNALS if kw in text)
        if article.source in ("机器之心", "量子位"):
            score += 5
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
