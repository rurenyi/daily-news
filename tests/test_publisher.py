from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from daily_news.publishers.biliup import _extract_bvid, _resolve_biliup_binary, _run_command_with_live_output


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

    def test_run_command_with_live_output_reports_status_lines(self) -> None:
        process = MagicMock()
        chunks = iter(list("speed 1MB/s\rdone\n") + [""])
        process.stdout.read.side_effect = lambda _size: next(chunks, "")
        process.poll.side_effect = [None] * 20 + [0]
        process.wait.return_value = 0
        callback = MagicMock()

        with patch("daily_news.publishers.biliup.subprocess.Popen", return_value=process):
            return_code, output = _run_command_with_live_output(["biliup"], status_callback=callback)

        self.assertEqual(return_code, 0)
        self.assertEqual(output, "speed 1MB/s\ndone")
        callback.assert_any_call("speed 1MB/s")
        callback.assert_any_call("done")


if __name__ == "__main__":
    unittest.main()
