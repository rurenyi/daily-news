from __future__ import annotations

from daily_news.models import ArticleContent, SummaryResult
from daily_news.summarizers.base import Summarizer
from daily_news.utils import compact_text


class MockSummarizer(Summarizer):
    def summarize(self, article: ArticleContent) -> SummaryResult:
        paragraphs = [compact_text(line) for line in article.content_text.splitlines() if compact_text(line)]
        summary = "；".join(paragraphs[:2])[:220] or article.article.title
        key_points = paragraphs[:3] or [article.article.title]
        script = (
            f"今天带你快速了解《{article.article.title}》。"
            f"这篇内容的核心结论是：{summary}。"
            f"如果你想看原文，可以查看视频简介里的来源链接。"
        )
        return SummaryResult(
            headline=article.article.title,
            summary=summary,
            key_points=key_points,
            script=script,
        )
