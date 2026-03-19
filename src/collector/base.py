from abc import ABC, abstractmethod
from datetime import datetime
from src.models import RawArticle


class BaseCollector(ABC):
    """采集器基类"""

    name: str = "unknown"

    @abstractmethod
    def fetch(self, since: datetime) -> list[RawArticle]:
        """采集指定时间之后的文章"""
        ...
