from __future__ import annotations

import unittest

from daily_news.models import SummaryResult
from daily_news.video.simple_renderer import select_cover_text


class RendererTests(unittest.TestCase):
    def test_select_cover_text_prefers_headline(self) -> None:
        summary = SummaryResult(
            headline="Claude Opus 4.7 发布：编程更强、视觉更清、自主性飞跃",
            summary="摘要",
            key_points=["要点一", "要点二"],
            script="脚本",
        )
        self.assertEqual(select_cover_text(summary), "Claude Opus 4.7 发布：编程更强、视觉更清、自主性飞跃")

    def test_select_cover_text_falls_back_to_key_point(self) -> None:
        summary = SummaryResult(
            headline="这是一条特别特别长的标题" * 8,
            summary="摘要",
            key_points=["最重要的结论：模型编程能力显著增强", "其他"],
            script="脚本",
        )
        self.assertEqual(select_cover_text(summary), "最重要的结论：模型编程能力显著增强")


if __name__ == "__main__":
    unittest.main()
