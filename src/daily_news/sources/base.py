from __future__ import annotations

from abc import ABC, abstractmethod

from daily_news.models import ArticleContent, DiscoveredArticle


class SourceAdapter(ABC):
    @abstractmethod
    def discover(self, limit: int) -> list[DiscoveredArticle]:
        raise NotImplementedError

    @abstractmethod
    def fetch(self, article: DiscoveredArticle) -> ArticleContent:
        raise NotImplementedError

    def close(self) -> None:
        return None
