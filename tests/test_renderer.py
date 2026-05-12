from __future__ import annotations

import unittest
from unittest.mock import patch

from daily_news.models import SummaryResult
from daily_news.video.simple_renderer import _find_font_path, select_cover_text


class RendererTests(unittest.TestCase):
    def test_find_font_path_prefers_existing_linux_cjk_font(self) -> None:
        _find_font_path.cache_clear()
        with (
            patch("daily_news.video.simple_renderer._font_candidates", return_value=["/fake/linux-cjk.ttf"]),
            patch("daily_news.video.simple_renderer.Path.exists", return_value=True),
        ):
            self.assertEqual(_find_font_path(False), "/fake/linux-cjk.ttf")

    def test_select_cover_text_prefers_headline(self) -> None:
        summary = SummaryResult(
            headline="Claude Opus 4.7 发布：编程更强、视觉更清、自主性飞跃",
            summary="摘要",
            key_points=["要点一", "要点二"],
            script="脚本",
        )
        self.assertEqual(select_cover_text(summary), "Claude Opus 4.7 发布：编程...")

    def test_select_cover_text_falls_back_to_key_point(self) -> None:
        summary = SummaryResult(
            headline="这是一条特别特别长的标题" * 8,
            summary="摘要",
            key_points=["最重要的结论：模型编程能力显著增强", "其他"],
            script="脚本",
        )
        self.assertEqual(select_cover_text(summary), "最重要的结论：模型编程能力显著增强")

    def test_select_cover_text_uses_short_key_point_when_available(self) -> None:
        summary = SummaryResult(
            headline="这是一条特别特别长的标题" * 8,
            summary="摘要",
            key_points=["模型编程能力显著增强", "其他"],
            script="脚本",
        )
        self.assertEqual(select_cover_text(summary), "模型编程能力显著增强")


if __name__ == "__main__":
    unittest.main()
