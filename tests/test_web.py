from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from daily_news.config import AppConfig
from daily_news.models import ArticleContent, DiscoveredArticle, PublishResult, RenderResult, SummaryResult
from daily_news.storage.sqlite_store import SqliteArticleStore
from daily_news.web.app import create_app


class WebAppTests(unittest.TestCase):
    def test_articles_pages_show_summary_and_links(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config = AppConfig(database_path=str(temp_path / "state.db"), workspace_dir=str(temp_path))
            store = SqliteArticleStore(Path(config.database_path))
            article = DiscoveredArticle(
                source_name="anthropic",
                external_id="sample-article",
                url="https://example.com/article",
                title="Sample Article",
            )
            store.upsert_discovery(article)
            store.save_fetch(ArticleContent(article=article, content_text="original body", content_hash="hash"))
            store.save_summary(
                "sample-article",
                SummaryResult(
                    headline="中文标题",
                    summary="这是摘要内容",
                    key_points=["要点一", "要点二"],
                    script="这是播报稿",
                ),
            )
            video_path = temp_path / "video.mp4"
            cover_path = temp_path / "cover.png"
            video_path.write_bytes(b"video")
            cover_path.write_bytes(b"cover")
            store.save_video(
                "sample-article",
                RenderResult(video_path=str(video_path), cover_path=str(cover_path)),
            )
            store.mark_published(
                "sample-article",
                PublishResult(
                    remote_id="BV1xx411c7mD",
                    remote_url="https://www.bilibili.com/video/BV1xx411c7mD",
                    raw_output="ok",
                ),
            )
            store.close()

            client = TestClient(create_app(config))
            list_response = client.get("/articles")
            self.assertEqual(list_response.status_code, 200)
            self.assertIn("https://example.com/article", list_response.text)
            self.assertIn("这是摘要内容", list_response.text)
            self.assertIn("https://www.bilibili.com/video/BV1xx411c7mD", list_response.text)

            detail_response = client.get("/articles/sample-article")
            self.assertEqual(detail_response.status_code, 200)
            self.assertIn("这是播报稿", detail_response.text)
            self.assertIn("已发布", detail_response.text)


if __name__ == "__main__":
    unittest.main()
