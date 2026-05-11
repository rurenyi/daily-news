from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from daily_news.publishers.biliup import _extract_bvid, _resolve_biliup_binary


class PublisherTests(unittest.TestCase):
    def test_extract_bvid(self) -> None:
        output = "Upload complete. BV1xx411c7mD published successfully."
        self.assertEqual(_extract_bvid(output), "BV1xx411c7mD")

    def test_resolve_binary_prefers_direct_path(self) -> None:
        with patch.object(Path, "exists", return_value=True):
            self.assertEqual(_resolve_biliup_binary("./.venv/bin/biliup"), str(Path("./.venv/bin/biliup")))

    def test_resolve_binary_uses_which(self) -> None:
        with patch("daily_news.publishers.biliup.shutil.which", return_value="/usr/local/bin/biliup"):
            self.assertEqual(_resolve_biliup_binary("biliup"), "/usr/local/bin/biliup")


if __name__ == "__main__":
    unittest.main()
