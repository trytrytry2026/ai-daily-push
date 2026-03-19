"""
AI 日报 — 每日自动采集 AI 资讯 + 论文，生成精美网页日报
"""
import logging
import sys
from datetime import datetime, timezone, timedelta

from src.config import RSS_FEEDS, MAX_PAPER_COUNT
from src.collector.rss_collector import RSSCollector
from src.collector.web_collector import Kr36Collector, BaiduNewsCollector
from src.collector.cn_paper_collector import CnPaperCollector
from src.filter.pipeline import run_filter_pipeline, validate_urls
from src.ranker.hot_ranker import rank_articles
from src.summarizer.deepseek import summarize_articles
from src.summarizer.paper_summarizer import summarize_papers
from src.generator.page_builder import generate_daily_page

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def main():
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)
    logger.info(f"=== AI 日报生成开始 === 采集时间范围: {since.isoformat()} ~ {now.isoformat()}")

    # ── 1. 采集新闻 ──
    news_list = _collect_and_process_news(since)

    # ── 2. 采集论文（独立流程） ──
    paper_list = _collect_and_process_papers()

    # ── 3. 生成日报 HTML ──
    rel_path = generate_daily_page(
        news_list=news_list,
        paper_list=paper_list,
        date=now,
    )

    logger.info(f"=== AI 日报生成完成 === 页面路径: site/{rel_path}")
    logger.info(f"共推送 {len(news_list)} 条资讯 + {len(paper_list)} 篇论文")


def _collect_and_process_news(since: datetime):
    """新闻采集 → 排序 → 过滤 → URL校验 → LLM摘要 → 字符控制"""
    collectors = [
        Kr36Collector(),
        BaiduNewsCollector(),
    ]
    for name, feed_url in RSS_FEEDS.items():
        collectors.append(RSSCollector(name=name, feed_url=feed_url))

    all_articles = []
    for collector in collectors:
        try:
            articles = collector.fetch(since)
            all_articles.extend(articles)
        except Exception as e:
            logger.error(f"采集器 {collector.name} 异常: {e}")

    logger.info(f"共采集到 {len(all_articles)} 条原始文章")

    if not all_articles:
        logger.warning("未采集到任何新闻文章")
        return []

    all_articles = rank_articles(all_articles)
    filtered = run_filter_pipeline(all_articles, since)

    if not filtered:
        logger.warning("过滤后无文章，放宽条件重试...")
        filtered = all_articles[:10]

    filtered = validate_urls(filtered)
    news_list = summarize_articles(filtered)
    news_list = _truncate_to_limit(news_list, max_chars=3000)
    return news_list


def _collect_and_process_papers():
    """中文论文采集 → 去重 → LLM精炼摘要"""
    try:
        collector = CnPaperCollector()
        since_papers = datetime.now(timezone.utc) - timedelta(days=7)
        raw_papers = collector.fetch(since_papers)
    except Exception as e:
        logger.error(f"论文采集异常: {e}")
        return []

    if not raw_papers:
        logger.warning("未采集到论文")
        return []

    logger.info(f"采集到 {len(raw_papers)} 篇中文论文解读，开始精炼摘要...")
    paper_list = summarize_papers(raw_papers, max_count=MAX_PAPER_COUNT)
    return paper_list


def _generate_empty_page(now):
    from src.generator.page_builder import generate_daily_page
    generate_daily_page(news_list=[], paper_list=[], date=now)


def _truncate_to_limit(articles, max_chars=3000):
    """确保总输出字符不超限"""
    total = 0
    result = []
    for a in articles:
        chars = len(a.title) + len(a.description) + len(a.source) + 20  # 20 for formatting overhead
        if total + chars > max_chars and len(result) >= 10:
            break
        total += chars
        result.append(a)
    return result


if __name__ == "__main__":
    main()
