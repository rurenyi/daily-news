from __future__ import annotations

from abc import ABC, abstractmethod
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
    ) -> PublishResult:
        raise NotImplementedError


class NullPublisher(Publisher):
    def publish(
        self,
        article: ArticleContent,
        summary: SummaryResult,
        video_path: Path,
        cover_path: Path,
    ) -> PublishResult:
        return PublishResult(remote_id=None, remote_url=None, raw_output="Publishing skipped.")
