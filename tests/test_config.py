from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from daily_news.config import load_config


class ConfigTests(unittest.TestCase):
    def test_load_config_supports_multiple_sources(self) -> None:
        payload = {
            "sources": [
                {
                    "name": "anthropic-news",
                    "enabled": True,
                    "provider": "anthropic",
                    "listing_url": "https://www.anthropic.com/news",
                    "article_path_prefix": "/news/",
                },
                {
                    "name": "anthropic-research",
                    "enabled": False,
                    "provider": "anthropic",
                    "listing_url": "https://www.anthropic.com/research",
                    "article_path_prefix": "/research/",
                    "id_prefix": "research-",
                },
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            config = load_config(path)

        self.assertEqual(len(config.sources), 2)
        self.assertEqual(len(config.enabled_sources), 1)
        self.assertEqual(config.enabled_sources[0].name, "anthropic-news")
        self.assertEqual(config.sources[1].id_prefix, "research-")

    def test_load_config_supports_legacy_single_source(self) -> None:
        payload = {
            "source": {
                "name": "anthropic-news",
                "listing_url": "https://www.anthropic.com/news",
            }
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            config = load_config(path)

        self.assertEqual(len(config.sources), 1)
        self.assertEqual(config.source.name, "anthropic-news")
