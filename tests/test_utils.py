from __future__ import annotations

import unittest

from daily_news.utils import extract_json_object


class UtilsTests(unittest.TestCase):
    def test_extract_json_object_from_fenced_block(self) -> None:
        payload = extract_json_object(
            """```json
            {"headline":"标题","summary":"摘要","key_points":["a"],"script":"b"}
            ```"""
        )
        self.assertEqual(payload["headline"], "标题")


if __name__ == "__main__":
    unittest.main()
