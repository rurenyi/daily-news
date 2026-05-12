from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from daily_news.models import ArticleContent, DiscoveredArticle, PublishResult, RenderResult, SummaryResult
from daily_news.utils import ensure_parent, utc_now_iso


class SqliteArticleStore:
    def __init__(self, database_path: Path):
        ensure_parent(database_path)
        self._database_path = database_path
        self._connection = sqlite3.connect(database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._initialize()

    def _initialize(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS articles (
                external_id TEXT PRIMARY KEY,
                source_name TEXT NOT NULL,
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                published_at TEXT,
                author TEXT,
                status TEXT NOT NULL,
                last_error_stage TEXT,
                last_error TEXT,
                content_text TEXT,
                content_hash TEXT,
                page_html_path TEXT,
                page_pdf_path TEXT,
                page_screenshot_path TEXT,
                summary_json TEXT,
                summary_text_path TEXT,
                audio_path TEXT,
                video_path TEXT,
                cover_path TEXT,
                publish_output TEXT,
                published_video_id TEXT,
                published_video_url TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status);
            """
        )
        self._ensure_column("articles", "published_video_url", "TEXT")
        self._ensure_column("articles", "page_html_path", "TEXT")
        self._ensure_column("articles", "page_pdf_path", "TEXT")
        self._ensure_column("articles", "page_screenshot_path", "TEXT")
        self._ensure_column("articles", "summary_text_path", "TEXT")
        self._connection.commit()

    def _ensure_column(self, table_name: str, column_name: str, definition: str) -> None:
        existing_columns = {
            row["name"]
            for row in self._connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        if column_name not in existing_columns:
            self._connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")

    def close(self) -> None:
        self._connection.close()

    def upsert_discovery(self, article: DiscoveredArticle) -> bool:
        existing = self.get_article(article.external_id)
        now = utc_now_iso()
        if existing:
            self._connection.execute(
                """
                UPDATE articles
                SET url = ?, title = ?, published_at = COALESCE(?, published_at), author = COALESCE(?, author), updated_at = ?
                WHERE external_id = ?
                """,
                (article.url, article.title, article.published_at, article.author, now, article.external_id),
            )
            self._connection.commit()
            return False
        self._connection.execute(
            """
            INSERT INTO articles (
                external_id, source_name, url, title, published_at, author, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'discovered', ?, ?)
            """,
            (
                article.external_id,
                article.source_name,
                article.url,
                article.title,
                article.published_at,
                article.author,
                now,
                now,
            ),
        )
        self._connection.commit()
        return True

    def list_pending(self, limit: int) -> list[sqlite3.Row]:
        cursor = self._connection.execute(
            """
            SELECT * FROM articles
            WHERE status != 'published'
            ORDER BY COALESCE(published_at, created_at) DESC, created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return cursor.fetchall()

    def list_articles(self) -> list[sqlite3.Row]:
        return self._connection.execute(
            """
            SELECT external_id, title, status, url, updated_at, published_video_url
            FROM articles
            ORDER BY updated_at DESC
            """
        ).fetchall()

    def list_for_admin(self) -> list[sqlite3.Row]:
        return self._connection.execute(
            """
            SELECT
                external_id,
                source_name,
                title,
                url,
                status,
                summary_json,
                summary_text_path,
                video_path,
                cover_path,
                published_video_id,
                published_video_url,
                last_error_stage,
                last_error,
                updated_at,
                created_at
            FROM articles
            ORDER BY updated_at DESC, created_at DESC
            """
        ).fetchall()

    def get_for_admin(self, external_id: str) -> sqlite3.Row | None:
        return self._connection.execute(
            """
            SELECT
                external_id,
                source_name,
                title,
                url,
                published_at,
                author,
                status,
                content_text,
                page_html_path,
                page_pdf_path,
                page_screenshot_path,
                summary_json,
                summary_text_path,
                audio_path,
                video_path,
                cover_path,
                publish_output,
                published_video_id,
                published_video_url,
                last_error_stage,
                last_error,
                updated_at,
                created_at
            FROM articles
            WHERE external_id = ?
            """,
            (external_id,),
        ).fetchone()

    def get_article(self, external_id: str) -> sqlite3.Row | None:
        return self._connection.execute(
            "SELECT * FROM articles WHERE external_id = ?",
            (external_id,),
        ).fetchone()

    def save_fetch(self, article: ArticleContent) -> None:
        self._connection.execute(
            """
            UPDATE articles
            SET title = ?, published_at = COALESCE(?, published_at), author = COALESCE(?, author),
                content_text = ?, content_hash = ?, page_html_path = ?, page_pdf_path = ?, page_screenshot_path = ?,
                status = 'fetched', last_error_stage = NULL, last_error = NULL, updated_at = ?
            WHERE external_id = ?
            """,
            (
                article.article.title,
                article.article.published_at,
                article.article.author,
                article.content_text,
                article.content_hash,
                article.page_html_path,
                article.page_pdf_path,
                article.page_screenshot_path,
                utc_now_iso(),
                article.article.external_id,
            ),
        )
        self._connection.commit()

    def save_summary(self, external_id: str, summary: SummaryResult, summary_text_path: Path | None = None) -> None:
        self._connection.execute(
            """
            UPDATE articles
            SET summary_json = ?, summary_text_path = ?, status = 'summarized',
                last_error_stage = NULL, last_error = NULL, updated_at = ?
            WHERE external_id = ?
            """,
            (
                json.dumps(summary.as_dict(), ensure_ascii=False),
                str(summary_text_path) if summary_text_path is not None else None,
                utc_now_iso(),
                external_id,
            ),
        )
        self._connection.commit()

    def save_summary_text_path(self, external_id: str, summary_text_path: Path) -> None:
        self._connection.execute(
            """
            UPDATE articles
            SET summary_text_path = ?, updated_at = ?
            WHERE external_id = ?
            """,
            (str(summary_text_path), utc_now_iso(), external_id),
        )
        self._connection.commit()

    def save_audio(self, external_id: str, audio_path: Path) -> None:
        self._connection.execute(
            """
            UPDATE articles
            SET audio_path = ?, status = 'audio_generated', last_error_stage = NULL, last_error = NULL, updated_at = ?
            WHERE external_id = ?
            """,
            (str(audio_path), utc_now_iso(), external_id),
        )
        self._connection.commit()

    def save_video(self, external_id: str, render_result: RenderResult) -> None:
        self._connection.execute(
            """
            UPDATE articles
            SET video_path = ?, cover_path = ?, status = 'video_rendered', last_error_stage = NULL, last_error = NULL, updated_at = ?
            WHERE external_id = ?
            """,
            (render_result.video_path, render_result.cover_path, utc_now_iso(), external_id),
        )
        self._connection.commit()

    def mark_published(self, external_id: str, result: PublishResult) -> None:
        self._connection.execute(
            """
            UPDATE articles
            SET status = 'published', publish_output = ?, published_video_id = ?, published_video_url = ?,
                last_error_stage = NULL, last_error = NULL, updated_at = ?
            WHERE external_id = ?
            """,
            (result.raw_output, result.remote_id, result.remote_url, utc_now_iso(), external_id),
        )
        self._connection.commit()

    def mark_failure(self, external_id: str, stage: str, error_message: str) -> None:
        self._connection.execute(
            """
            UPDATE articles
            SET status = ?, last_error_stage = ?, last_error = ?, updated_at = ?
            WHERE external_id = ?
            """,
            (f"{stage}_failed", stage, error_message[:2000], utc_now_iso(), external_id),
        )
        self._connection.commit()
