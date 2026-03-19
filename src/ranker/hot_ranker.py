import logging

from src.config import INDUSTRY_KEYWORDS, COMPANY_KEYWORDS
from src.models import RawArticle

logger = logging.getLogger(__name__)

COMPANY_WEIGHT = {
    "华为": 3, "英伟达": 3, "NVIDIA": 3, "OpenAI": 3,
    "阿里": 2, "腾讯": 2, "字节": 2, "百度": 2, "谷歌": 2, "Google": 2,
    "小米": 1, "Meta": 1, "微软": 1, "Microsoft": 1,
    "DeepSeek": 2, "Kimi": 1, "智谱": 1,
}

INDUSTRY_WEIGHT = {
    "大模型": 3, "Agent": 3, "智能体": 3,
    "算力": 2, "AI芯片": 2, "多模态": 2,
    "AI应用": 1, "AIGC": 1, "RAG": 1,
}


def rank_articles(articles: list[RawArticle]) -> list[RawArticle]:
    """按热度评分排序"""
    for article in articles:
        article.keywords = getattr(article, "keywords", [])
        score = _calc_score(article)
        article._score = score  # type: ignore

    articles.sort(key=lambda a: getattr(a, "_score", 0), reverse=True)
    logger.info(f"排序完成，Top3 分数: {[getattr(a, '_score', 0) for a in articles[:3]]}")
    return articles


def _calc_score(article: RawArticle) -> float:
    text = f"{article.title} {article.summary}".lower()
    score = 0.0

    for kw, w in COMPANY_WEIGHT.items():
        if kw.lower() in text:
            score += w

    for kw, w in INDUSTRY_WEIGHT.items():
        if kw.lower() in text:
            score += w

    if len(article.summary) > 100:
        score += 1

    return score
