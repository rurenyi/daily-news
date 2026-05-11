from __future__ import annotations

import json
from pathlib import Path

from daily_news.config import AppConfig
from daily_news.models import ArticleContent, DiscoveredArticle, SummaryResult
from daily_news.publishers.base import Publisher
from daily_news.sources.base import SourceAdapter
from daily_news.storage.sqlite_store import SqliteArticleStore
from daily_news.summarizers.base import Summarizer
from daily_news.tts.base import TextToSpeech
from daily_news.utils import slugify
from daily_news.video.simple_renderer import SimpleVideoRenderer


class DailyNewsPipeline:
    def __init__(
        self,
        config: AppConfig,
        store: SqliteArticleStore,
        source: SourceAdapter,
        summarizer: Summarizer,
        tts: TextToSpeech,
        renderer: SimpleVideoRenderer,
        publisher: Publisher,
    ):
        self._config = config
        self._store = store
        self._source = source
        self._summarizer = summarizer
        self._tts = tts
        self._renderer = renderer
        self._publisher = publisher
        self._audio_dir = config.workspace_path / "audio"
        self._video_dir = config.workspace_path / "video"

    def close(self) -> None:
        if hasattr(self._source, "close"):
            self._source.close()

    def discover(self, limit: int | None = None) -> dict:
        limit = limit or self._config.max_articles_per_run
        discovered = self._source.discover(limit)
        inserted = 0
        for article in discovered:
            inserted += int(self._store.upsert_discovery(article))
        return {"discovered": len(discovered), "new": inserted}

    def run_once(self, limit: int | None = None) -> dict:
        discovery_report = self.discover(limit)
        pending = self._store.list_pending(limit or self._config.max_articles_per_run)
        processed = 0
        published = 0
        failed = 0

        for row in pending:
            processed += 1
            external_id = row["external_id"]
            stage = "fetch"
            discovered_article = DiscoveredArticle(
                source_name=row["source_name"],
                external_id=external_id,
                url=row["url"],
                title=row["title"],
                published_at=row["published_at"],
                author=row["author"],
            )
            try:
                article = self._get_or_fetch_article(row, discovered_article)
                stage = "summary"
                summary = self._get_or_summarize(row, article)
                stage = "tts"
                audio_path = self._get_or_generate_audio(row, external_id, summary)
                stage = "video"
                render_result = self._get_or_render_video(row, external_id, article, summary, audio_path)
                if self._config.publisher.enabled:
                    stage = "publish"
                    publish_result = self._publisher.publish(
                        article=article,
                        summary=summary,
                        video_path=Path(render_result.video_path),
                        cover_path=Path(render_result.cover_path),
                    )
                    self._store.mark_published(external_id, publish_result)
                    published += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                self._store.mark_failure(external_id, stage, str(exc))
        return {
            "discovered": discovery_report["discovered"],
            "new": discovery_report["new"],
            "processed": processed,
            "published": published,
            "failed": failed,
        }

    def _get_or_fetch_article(self, row, article: DiscoveredArticle) -> ArticleContent:
        if row["content_text"] and row["status"] not in {"discovered", "fetch_failed"}:
            return ArticleContent(article=article, content_text=row["content_text"], content_hash=row["content_hash"])
        fetched = self._source.fetch(article)
        self._store.save_fetch(fetched)
        return fetched

    def _get_or_summarize(self, row, article: ArticleContent) -> SummaryResult:
        if row["summary_json"] and row["status"] not in {"fetched", "summary_failed", "discovered", "fetch_failed"}:
            payload = json.loads(row["summary_json"])
            return SummaryResult(
                headline=payload["headline"],
                summary=payload["summary"],
                key_points=list(payload["key_points"]),
                script=payload["script"],
            )
        summary = self._summarizer.summarize(article)
        self._store.save_summary(article.article.external_id, summary)
        return summary

    def _get_or_generate_audio(self, row, external_id: str, summary: SummaryResult) -> Path:
        if row["audio_path"] and row["status"] not in {"summarized", "tts_failed", "fetched", "summary_failed"}:
            return Path(row["audio_path"])
        audio_path = self._audio_dir / f"{external_id}-{slugify(summary.headline)}.mp3"
        self._tts.synthesize(summary.script, audio_path)
        self._store.save_audio(external_id, audio_path)
        return audio_path

    def _get_or_render_video(
        self,
        row,
        external_id: str,
        article: ArticleContent,
        summary: SummaryResult,
        audio_path: Path,
    ):
        if row["video_path"] and row["cover_path"] and row["status"] not in {"audio_generated", "video_failed"}:
            from daily_news.models import RenderResult

            return RenderResult(video_path=row["video_path"], cover_path=row["cover_path"])
        output_path = self._video_dir / f"{external_id}-{slugify(summary.headline)}.mp4"
        render_result = self._renderer.render(summary, article.article.url, audio_path, output_path)
        self._store.save_video(external_id, render_result)
        return render_result
