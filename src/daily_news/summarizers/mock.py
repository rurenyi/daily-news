from __future__ import annotations

from daily_news.models import ArticleContent, SummaryResult
from daily_news.summarizers.base import Summarizer
from daily_news.utils import compact_text


class MockSummarizer(Summarizer):
    def summarize(self, article: ArticleContent) -> SummaryResult:
        paragraphs = [compact_text(line) for line in article.content_text.splitlines() if compact_text(line)]
        translated_excerpt = "；".join(paragraphs[:3])[:360] or article.article.title
        summary = (
            f"以下是《{article.article.title}》的中文翻译讲解：{translated_excerpt}。"
            "这段内容保留原文关键信息，并用更容易理解的中文把重点串起来。"
        )
        key_points = [f"原文重点：{paragraph}" for paragraph in paragraphs[:1]]
        key_points.extend(f"延伸理解：{paragraph}" for paragraph in paragraphs[1:3])
        if not key_points:
            key_points = [f"原文重点：{article.article.title}"]
        script = (
            f"今天我们不只做摘要，而是直接翻译并讲解《{article.article.title}》。"
            f"{summary}"
            f"如果你想看原文，可以查看视频简介里的来源链接。"
        )
        return SummaryResult(
            headline=article.article.title,
            summary=summary,
            key_points=key_points,
            script=script,
        )
