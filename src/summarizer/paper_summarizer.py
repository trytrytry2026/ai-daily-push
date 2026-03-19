"""论文摘要翻译模块 — 将英文论文标题和摘要翻译成中文"""
import json
import logging

from openai import OpenAI

from src.config import DEEPSEEK_API_KEY
from src.models import RawArticle, ProcessedArticle

logger = logging.getLogger(__name__)

PAPER_SYSTEM_PROMPT = """你是一位AI领域的科技编辑，负责将英文AI论文翻译成通俗易懂的中文摘要，面向非技术背景的企业管理者。

要求：
1. 中文标题：用一句话概括论文核心发现/贡献，25字以内，要通俗易懂、有信息量
2. 中文描述：用大白话解释这篇论文做了什么、有什么价值，60字以内，不要堆砌术语

输出严格的JSON格式（不要markdown代码块）：
{"title": "中文标题", "desc": "中文描述"}"""

PAPER_USER_TEMPLATE = """英文标题：{title}
英文摘要：{summary}"""


def summarize_papers(papers: list[RawArticle], max_count: int = 10) -> list[ProcessedArticle]:
    """翻译论文为中文标题+描述，返回最多 max_count 篇"""
    papers = papers[:max_count]

    if not DEEPSEEK_API_KEY:
        logger.warning("未配置 DEEPSEEK_API_KEY，使用原始英文标题")
        return [_fallback(p) for p in papers]

    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    results = []

    for paper in papers:
        try:
            processed = _translate_one(client, paper)
            results.append(processed)
        except Exception as e:
            logger.error(f"论文翻译失败: {paper.title[:50]} -> {e}")
            results.append(_fallback(paper))

    return results


def _translate_one(client: OpenAI, paper: RawArticle) -> ProcessedArticle:
    user_msg = PAPER_USER_TEMPLATE.format(
        title=paper.title,
        summary=paper.summary[:400] if paper.summary else "无摘要",
    )

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": PAPER_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.3,
        max_tokens=200,
    )

    content = response.choices[0].message.content.strip()
    content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        data = json.loads(content)
        title = data.get("title", paper.title)
        desc = data.get("desc", "")
    except json.JSONDecodeError:
        logger.warning(f"JSON 解析失败: {content[:100]}")
        title = paper.title
        desc = paper.summary[:100] if paper.summary else ""

    return ProcessedArticle(
        title=title,
        description=desc,
        url=paper.url,
        source="arXiv",
        publish_time=paper.publish_time,
    )


def _fallback(paper: RawArticle) -> ProcessedArticle:
    return ProcessedArticle(
        title=paper.title,
        description=paper.summary[:150] if paper.summary else "",
        url=paper.url,
        source="arXiv",
        publish_time=paper.publish_time,
    )
