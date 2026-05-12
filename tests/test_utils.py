from __future__ import annotations

import unittest

from daily_news.utils import extract_json_object, strip_markdown_formatting


class UtilsTests(unittest.TestCase):
    def test_extract_json_object_from_fenced_block(self) -> None:
        payload = extract_json_object(
            """```json
            {"headline":"标题","summary":"摘要","key_points":["a"],"script":"b"}
            ```"""
        )
        self.assertEqual(payload["headline"], "标题")

    def test_strip_markdown_formatting_removes_common_markdown(self) -> None:
        text = "# 标题\n- **第一点**\n- [链接](https://example.com)\n```python\nprint('x')\n```"
        self.assertEqual(strip_markdown_formatting(text), "标题\n第一点\n链接\nprint('x')")


if __name__ == "__main__":
    unittest.main()
