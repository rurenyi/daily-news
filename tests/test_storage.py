from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from daily_news.models import ArticleContent, DiscoveredArticle, PublishResult, RenderResult, SummaryResult
from daily_news.storage.sqlite_store import SqliteArticleStore


class SqliteStoreTests(unittest.TestCase):
    def test_article_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SqliteArticleStore(Path(temp_dir) / "state.db")
            article = DiscoveredArticle(
                source_name="anthropic",
                external_id="sample-1",
                url="https://example.com/a",
                title="Sample",
            )
            self.assertTrue(store.upsert_discovery(article))
            content = ArticleContent(article=article, content_text="hello world", content_hash="hash")
            store.save_fetch(content)
            store.save_summary(
                "sample-1",
                SummaryResult(
                    headline="标题",
                    summary="摘要",
                    key_points=["要点1", "要点2"],
                    script="播报稿",
                ),
                Path("summary.txt"),
            )
            store.save_audio("sample-1", Path("audio.mp3"))
            store.save_video("sample-1", RenderResult(video_path="video.mp4", cover_path="cover.png"))
            store.mark_published(
                "sample-1",
                PublishResult(remote_id="BV1xx", remote_url="https://www.bilibili.com/video/BV1xx", raw_output="ok"),
            )

            row = store.get_article("sample-1")
            assert row is not None
            self.assertEqual(row["status"], "published")
            self.assertEqual(row["video_path"], "video.mp4")
            self.assertEqual(row["published_video_url"], "https://www.bilibili.com/video/BV1xx")
            self.assertEqual(row["summary_text_path"], "summary.txt")
            store.close()


if __name__ == "__main__":
    unittest.main()
