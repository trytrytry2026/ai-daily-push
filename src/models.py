from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RawArticle:
    """采集到的原始文章"""
    title: str
    summary: str
    url: str
    source: str
    publish_time: datetime
    keywords: list[str] = field(default_factory=list)


@dataclass
class ProcessedArticle:
    """经过过滤、摘要处理后的文章"""
    title: str          # LLM 生成的一句话标题
    description: str    # LLM 生成的精简描述
    url: str            # 原文链接（国内可直接访问）
    source: str         # 来源站点名
    publish_time: datetime
    score: float = 0.0  # 热度评分
