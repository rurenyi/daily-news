from __future__ import annotations

from collections import deque

from daily_news.models import ArticleContent, DiscoveredArticle
from daily_news.sources.base import SourceAdapter


class CompositeSourceAdapter(SourceAdapter):
    def __init__(self, sources: list[SourceAdapter]):
        self._sources = sources
        self._source_by_name = {source.name: source for source in sources if hasattr(source, "name")}

    def discover(self, limit: int) -> list[DiscoveredArticle]:
        discovered_per_source = [deque(source.discover(limit)) for source in self._sources]
        results: list[DiscoveredArticle] = []
        while len(results) < limit and any(queue for queue in discovered_per_source):
            for queue in discovered_per_source:
                if queue and len(results) < limit:
                    results.append(queue.popleft())
        return results

    def fetch(self, article: DiscoveredArticle) -> ArticleContent:
        source = self._source_by_name.get(article.source_name)
        if source is None:
            raise ValueError(f"Unable to find source adapter for '{article.source_name}'.")
        return source.fetch(article)

    def close(self) -> None:
        for source in self._sources:
            source.close()
