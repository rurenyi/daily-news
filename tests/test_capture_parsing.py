from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from daily_news.browser.base import CapturedPage
from daily_news.models import DiscoveredArticle
from daily_news.storage.sqlite_store import SqliteArticleStore


class CaptureStorageTests(unittest.TestCase):
    def test_store_persists_capture_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "state.db"
            store = SqliteArticleStore(db_path)
            article = DiscoveredArticle(
                source_name="anthropic",
                external_id="capture-1",
                url="https://example.com/article",
                title="Capture Test",
            )
            store.upsert_discovery(article)
            from daily_news.sources.anthropic import parse_article_html

            captured = CapturedPage(
                url=article.url,
                final_url=article.url,
                title=article.title,
                html="<html><body><article><p>Hello world</p><p>Second line</p><p>Third line</p></article></body></html>",
                html_path="capture.html",
                pdf_path="capture.pdf",
                screenshot_path="capture.png",
            )
            content = parse_article_html(captured.html, article, captured)
            store.save_fetch(content)
            row = store.get_article("capture-1")
            self.assertEqual(row["page_html_path"], "capture.html")
            self.assertEqual(row["page_pdf_path"], "capture.pdf")
            self.assertEqual(row["page_screenshot_path"], "capture.png")
            store.close()


if __name__ == "__main__":
    unittest.main()
