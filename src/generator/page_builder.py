import json
import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.models import ProcessedArticle

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
SITE_DIR = PROJECT_ROOT / "site"
ARCHIVE_FILE = SITE_DIR / "archive.json"

BJT = timezone(timedelta(hours=8))


def generate_daily_page(
    news_list: list[ProcessedArticle],
    paper_list: list[ProcessedArticle],
    date: datetime,
) -> str:
    """生成当天日报 HTML 页面，返回相对 URL 路径"""
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("daily.html")

    date_bjt = date.astimezone(BJT)
    date_str = date_bjt.strftime("%Y-%m-%d")
    weekday_map = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday = weekday_map[date_bjt.weekday()]
    date_display = f"{date_bjt.strftime('%Y年%m月%d日')} {weekday}"

    html = template.render(
        date_display=date_display,
        news_list=news_list,
        paper_list=paper_list,
        generated_at=datetime.now(BJT).strftime("%Y-%m-%d %H:%M"),
    )

    rel_path = f"{date_bjt.strftime('%Y/%m/%d')}.html"
    output_path = SITE_DIR / rel_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    logger.info(f"日报页面已生成: {output_path}")

    _update_archive(date_str, rel_path)
    _generate_index(env)

    return rel_path


def _update_archive(date_str: str, rel_path: str):
    archive = _load_archive()
    entry = {"date": date_str, "url": f"/{rel_path}"}
    archive = [a for a in archive if a["date"] != date_str]
    archive.insert(0, entry)
    archive = archive[:90]  # 保留最近 90 天
    ARCHIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVE_FILE.write_text(json.dumps(archive, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_archive() -> list[dict]:
    if ARCHIVE_FILE.exists():
        try:
            return json.loads(ARCHIVE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _generate_index(env: Environment):
    template = env.get_template("index.html")
    archive = _load_archive()

    latest = archive[0] if archive else None
    archives = archive[1:] if len(archive) > 1 else []

    html = template.render(latest=latest, archives=archives)
    index_path = SITE_DIR / "index.html"
    index_path.write_text(html, encoding="utf-8")
    logger.info(f"首页已更新: {index_path}")
