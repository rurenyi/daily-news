from __future__ import annotations

from abc import ABC, abstractmethod

from daily_news.models import ArticleContent, SummaryResult


class Summarizer(ABC):
    @abstractmethod
    def summarize(self, article: ArticleContent) -> SummaryResult:
        raise NotImplementedError
