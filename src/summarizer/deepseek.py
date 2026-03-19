import json
import logging

from openai import OpenAI

from src.config import DEEPSEEK_API_KEY
from src.models import RawArticle, ProcessedArticle

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一位资深AI行业编辑，为企业管理者撰写AI日报。

写作原则：
- 标题要有深度见解，揭示趋势、影响或背后的意义，不要只说"某公司发布了某产品"
- 可以用数据、对比、因果关系让标题更有信息量
- 好标题示例："AI医疗诊断提速7倍，但仅23%企业见到真金白银"
- 坏标题示例："某公司发布新产品"

输出要求：
1. title：一句话深度标题，20-30字，要有洞察力，不要标题党
2. desc：补充关键信息，50-80字，说清楚为什么重要、影响是什么

输出严格的JSON格式（不要markdown代码块）：
{"title": "...", "desc": "..."}"""

USER_PROMPT_TEMPLATE = """原标题：{title}
原文摘要：{summary}
来源：{source}"""


def summarize_articles(articles: list[RawArticle]) -> list[ProcessedArticle]:
    """批量调用 DeepSeek 生成摘要"""
    if not DEEPSEEK_API_KEY:
        logger.warning("未配置 DEEPSEEK_API_KEY，使用原始标题")
        return [_fallback(a) for a in articles]

    client = OpenAI(
        api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com",
        timeout=30.0, max_retries=2,
    )
    results = []

    for article in articles:
        try:
            processed = _summarize_one(client, article)
            results.append(processed)
        except Exception as e:
            logger.error(f"摘要生成失败: {article.title[:40]} -> {e}")
            results.append(_fallback(article))

    return results


def _summarize_one(client: OpenAI, article: RawArticle) -> ProcessedArticle:
    user_msg = USER_PROMPT_TEMPLATE.format(
        title=article.title,
        summary=article.summary[:300] if article.summary else "无摘要",
        source=article.source,
    )

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.3,
        max_tokens=200,
    )

    content = response.choices[0].message.content.strip()
    content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        data = json.loads(content)
        title = data.get("title", article.title)
        desc = data.get("desc", article.summary[:100])
    except json.JSONDecodeError:
        logger.warning(f"JSON 解析失败，使用原始标题: {content[:100]}")
        title = article.title
        desc = article.summary[:100] if article.summary else ""

    return ProcessedArticle(
        title=title,
        description=desc,
        url=article.url,
        source=article.source,
        publish_time=article.publish_time,
    )


def _fallback(article: RawArticle) -> ProcessedArticle:
    return ProcessedArticle(
        title=article.title,
        description=article.summary[:100] if article.summary else "",
        url=article.url,
        source=article.source,
        publish_time=article.publish_time,
    )
