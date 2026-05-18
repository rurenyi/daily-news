from __future__ import annotations

import unittest

from daily_news.utils import expand_acronyms_for_tts, extract_json_object, split_text_for_tts, strip_markdown_formatting


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

    def test_expand_acronyms_for_tts_spells_uppercase_tokens(self) -> None:
        text = "TAI 和 API 都需要单独读字母，但 Claude 不需要。"
        self.assertEqual(expand_acronyms_for_tts(text), "T A I 和 A P I 都需要单独读字母，但 Claude 不需要。")

    def test_split_text_for_tts_prefers_larger_paragraph_chunks(self) -> None:
        text = ("第一段内容。" * 80) + "\n\n" + ("第二段内容。" * 70) + "\n\n" + ("第三段内容。" * 60)
        chunks = split_text_for_tts(text, target_chars=120, hard_max_chars=180)
        self.assertLessEqual(len(chunks), 8)
        self.assertTrue(all(len(chunk) <= 180 for chunk in chunks))

    def test_split_text_for_tts_splits_long_paragraph_without_overfragmenting(self) -> None:
        text = "这是一个很长的段落，" * 120 + "结束。"
        chunks = split_text_for_tts(text, target_chars=120, hard_max_chars=180)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 180 for chunk in chunks))


if __name__ == "__main__":
    unittest.main()
