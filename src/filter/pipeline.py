import hashlib
import logging
import re
from collections import Counter
from datetime import datetime, timezone, timedelta

import requests

from src.config import (
    INDUSTRY_KEYWORDS, COMPANY_KEYWORDS, NEGATIVE_KEYWORDS,
    AI_APP_KEYWORDS, REQUEST_TIMEOUT, MAX_NEWS_COUNT, MIN_APP_DEPTH_COUNT,
)
from src.models import RawArticle

logger = logging.getLogger(__name__)


def run_filter_pipeline(articles: list[RawArticle], since: datetime) -> list[RawArticle]:
    """
    过滤 Pipeline：
    时间过滤 → 关键词匹配 → 质量过滤 → 去重 → 公司多样性控制 → 截取
    """
    logger.info(f"过滤前共 {len(articles)} 条文章")

    articles = filter_by_time(articles, since)
    logger.info(f"  时间过滤后: {len(articles)} 条")

    articles = filter_by_keywords(articles)
    logger.info(f"  关键词过滤后: {len(articles)} 条")

    articles = filter_by_quality(articles)
    logger.info(f"  质量过滤后: {len(articles)} 条")

    articles = deduplicate(articles)
    logger.info(f"  去重后: {len(articles)} 条")

    articles = ensure_diversity(articles)
    logger.info(f"  多样性控制后: {len(articles)} 条")

    articles = ensure_app_depth_mix(articles)
    logger.info(f"  AI应用深度保障后: {len(articles)} 条")

    articles = articles[:MAX_NEWS_COUNT]
    logger.info(f"最终保留 {len(articles)} 条文章")
    return articles


def filter_by_time(articles: list[RawArticle], since: datetime) -> list[RawArticle]:
    return [a for a in articles if a.publish_time >= since]


def filter_by_keywords(articles: list[RawArticle]) -> list[RawArticle]:
    """至少命中一个行业关键词或公司关键词"""
    all_keywords = INDUSTRY_KEYWORDS + COMPANY_KEYWORDS
    result = []
    for article in articles:
        text = f"{article.title} {article.summary}".lower()
        if any(kw.lower() in text for kw in all_keywords):
            matched = [kw for kw in all_keywords if kw.lower() in text]
            article.keywords = matched
            result.append(article)
    return result


def filter_by_quality(articles: list[RawArticle]) -> list[RawArticle]:
    """排除股评、自媒体、标题党"""
    result = []
    for article in articles:
        text = f"{article.title} {article.summary}"
        if any(neg.lower() in text.lower() for neg in NEGATIVE_KEYWORDS):
            continue
        if len(article.title) < 8:
            continue
        if _is_clickbait(article.title):
            continue
        result.append(article)
    return result


def _is_clickbait(title: str) -> bool:
    clickbait_patterns = [
        r"震惊", r"速看", r"赶紧收藏", r"不看后悔", r"必看",
        r"太疯狂了", r"吓一跳", r"万万没想到",
    ]
    return any(re.search(p, title) for p in clickbait_patterns)


def deduplicate(articles: list[RawArticle]) -> list[RawArticle]:
    """基于标题 SimHash 去重，相似度 > 0.7 的只保留第一条"""
    seen_hashes: list[int] = []
    seen_urls: set[str] = set()
    result = []

    for article in articles:
        url_key = re.sub(r"[?#].*$", "", article.url)
        if url_key in seen_urls:
            continue
        seen_urls.add(url_key)

        h = _simhash(article.title)
        if any(_hamming_similar(h, sh, threshold=0.7) for sh in seen_hashes):
            continue
        seen_hashes.append(h)
        result.append(article)

    return result


def _simhash(text: str, hash_bits: int = 64) -> int:
    tokens = list(text)
    v = [0] * hash_bits
    for token in tokens:
        token_hash = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
        for i in range(hash_bits):
            if token_hash & (1 << i):
                v[i] += 1
            else:
                v[i] -= 1
    fingerprint = 0
    for i in range(hash_bits):
        if v[i] > 0:
            fingerprint |= (1 << i)
    return fingerprint


def _hamming_similar(h1: int, h2: int, threshold: float = 0.7, bits: int = 64) -> bool:
    diff = bin(h1 ^ h2).count("1")
    similarity = 1 - diff / bits
    return similarity >= threshold


def ensure_diversity(articles: list[RawArticle]) -> list[RawArticle]:
    """同一公司最多保留 2 条"""
    company_count: Counter = Counter()
    result = []
    for article in articles:
        text = f"{article.title} {article.summary}".lower()
        companies_mentioned = [
            kw for kw in COMPANY_KEYWORDS if kw.lower() in text
        ]
        primary_company = companies_mentioned[0] if companies_mentioned else None
        if primary_company:
            if company_count[primary_company] >= 2:
                continue
            company_count[primary_company] += 1
        result.append(article)
    return result


def is_app_depth_article(article: RawArticle) -> bool:
    """判断文章是否属于 AI 应用/深度分析类"""
    text = f"{article.title} {article.summary}".lower()
    return any(kw.lower() in text for kw in AI_APP_KEYWORDS)


def ensure_app_depth_mix(articles: list[RawArticle]) -> list[RawArticle]:
    """保障至少 MIN_APP_DEPTH_COUNT 条 AI 应用深度类新闻排在前列"""
    app_articles = [a for a in articles if is_app_depth_article(a)]
    other_articles = [a for a in articles if not is_app_depth_article(a)]

    app_count = min(len(app_articles), max(MIN_APP_DEPTH_COUNT, len(app_articles)))

    result = app_articles[:app_count]
    remaining_slots = MAX_NEWS_COUNT - len(result)
    result.extend(other_articles[:remaining_slots])

    leftover_app = app_articles[app_count:]
    if len(result) < MAX_NEWS_COUNT and leftover_app:
        result.extend(leftover_app[:MAX_NEWS_COUNT - len(result)])

    return result[:MAX_NEWS_COUNT]


def validate_urls(articles: list[RawArticle]) -> list[RawArticle]:
    """校验 URL 是否可访问（HEAD 请求）"""
    result = []
    for article in articles:
        try:
            resp = requests.head(
                article.url, timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if resp.status_code < 400:
                result.append(article)
            else:
                logger.warning(f"URL 不可达 ({resp.status_code}): {article.url}")
        except Exception:
            logger.warning(f"URL 请求失败: {article.url}")
            result.append(article)  # 网络超时不一定是链接失效，保留
    return result
