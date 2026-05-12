from __future__ import annotations

import unittest

from daily_news.cli import format_article_table


class CliTableTests(unittest.TestCase):
    def test_format_article_table_renders_headers_and_rows(self) -> None:
        output = format_article_table(
            [
                {
                    "updated_at": "2026-05-12T10:00:00+00:00",
                    "status": "video_rendered",
                    "title": "Teaching Claude why",
                    "url": "https://www.anthropic.com/research/teaching-claude-why",
                },
                {
                    "updated_at": "2026-05-11T08:00:00+00:00",
                    "status": "published",
                    "title": "Natural Language Autoencoders",
                    "url": "https://www.anthropic.com/research/natural-language-autoencoders",
                },
            ]
        )

        self.assertIn("Updated", output)
        self.assertIn("Status", output)
        self.assertIn("Title", output)
        self.assertIn("URL", output)
        self.assertIn("Teaching Claude why", output)
        self.assertIn("video_rendered", output)

    def test_format_article_table_truncates_long_values(self) -> None:
        output = format_article_table(
            [
                {
                    "updated_at": "2026-05-12T10:00:00+00:00",
                    "status": "summary_failed_because_reason_is_very_long",
                    "title": "A" * 80,
                    "url": "https://example.com/" + "path/" * 30,
                }
            ]
        )

        self.assertIn("...", output)

    def test_format_article_table_handles_empty_rows(self) -> None:
        self.assertEqual(format_article_table([]), "No local article records.")


if __name__ == "__main__":
    unittest.main()
