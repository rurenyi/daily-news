from __future__ import annotations

import io
import unittest

from daily_news.progress import ConsoleProgressReporter


class NonInteractiveStringIO(io.StringIO):
    def isatty(self) -> bool:
        return False


class InteractiveStringIO(io.StringIO):
    def isatty(self) -> bool:
        return True


class ConsoleProgressReporterTests(unittest.TestCase):
    def test_non_interactive_stream_writes_newline_delimited_updates(self) -> None:
        stream = NonInteractiveStringIO()
        reporter = ConsoleProgressReporter(stream=stream, bar_width=10)

        reporter.discovery_started(5)
        reporter.discovery_completed(3, 2)
        reporter.run_started(total=2, publish_enabled=False)
        reporter.article_stage(1, 2, "article-1", "fetch", "A very useful title")
        reporter.article_finished(1, 2, "article-1", "video_rendered", "A very useful title")
        reporter.run_completed({"discovered": 3, "new": 2, "processed": 1, "published": 0, "failed": 0})

        output = stream.getvalue()
        self.assertIn("[discover] checking latest articles (limit=5)", output)
        self.assertIn("[discover] found 3 article(s), 2 new", output)
        self.assertIn("[run] queued 2 article(s), publish=off", output)
        self.assertIn("[----------] 0/2 article-1 -> fetch", output)
        self.assertIn("[#####-----] 1/2 article-1 -> video_rendered", output)
        self.assertIn("[run] done | discovered=3 new=2 processed=1 published=0 failed=0", output)

    def test_interactive_stream_uses_carriage_returns_and_final_newline(self) -> None:
        stream = InteractiveStringIO()
        reporter = ConsoleProgressReporter(stream=stream, bar_width=5)

        reporter.run_started(total=1, publish_enabled=True)
        reporter.article_stage(1, 1, "article-1", "summary", "Title")
        reporter.run_completed({"discovered": 1, "new": 1, "processed": 1, "published": 1, "failed": 0})

        output = stream.getvalue()
        self.assertGreaterEqual(output.count("\r"), 3)
        self.assertTrue(output.endswith("\n"))

    def test_interactive_stream_keeps_failure_message_visible(self) -> None:
        stream = InteractiveStringIO()
        reporter = ConsoleProgressReporter(stream=stream, bar_width=5)

        reporter.run_started(total=1, publish_enabled=False)
        reporter.article_stage(1, 1, "article-1", "tts", "Title")
        reporter.article_failed(1, 1, "article-1", "tts", "Edge TTS failed with some detailed error", "Title")
        reporter.run_completed({"discovered": 1, "new": 0, "processed": 1, "published": 0, "failed": 1})

        output = stream.getvalue()
        self.assertIn("failed at tts", output)
        self.assertIn("Edge TTS failed", output)
        self.assertIn("[run] done | discovered=1 new=0 processed=1 published=0 failed=1", output)
