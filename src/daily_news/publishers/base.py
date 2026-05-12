from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path

from daily_news.models import ArticleContent, PublishResult, SummaryResult


class Publisher(ABC):
    @abstractmethod
    def publish(
        self,
        article: ArticleContent,
        summary: SummaryResult,
        video_path: Path,
        cover_path: Path,
        status_callback: Callable[[str], None] | None = None,
    ) -> PublishResult:
        raise NotImplementedError


class NullPublisher(Publisher):
    def publish(
        self,
        article: ArticleContent,
        summary: SummaryResult,
        video_path: Path,
        cover_path: Path,
        status_callback: Callable[[str], None] | None = None,
    ) -> PublishResult:
        return PublishResult(remote_id=None, remote_url=None, raw_output="Publishing skipped.")
