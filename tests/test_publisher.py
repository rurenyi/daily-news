from __future__ import annotations

import unittest

from daily_news.publishers.biliup import _extract_bvid


class PublisherTests(unittest.TestCase):
    def test_extract_bvid(self) -> None:
        output = "Upload complete. BV1xx411c7mD published successfully."
        self.assertEqual(_extract_bvid(output), "BV1xx411c7mD")


if __name__ == "__main__":
    unittest.main()
