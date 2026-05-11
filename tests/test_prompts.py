from __future__ import annotations

import json
import unittest

from daily_news.models import ArticleContent, DiscoveredArticle
from daily_news.summarizers.prompts import (
    ANTHROPIC_PROMPT_PROFILE,
    DEFAULT_PROMPT_PROFILE,
    build_summary_messages,
    get_prompt_profile,
)


class PromptProfileTests(unittest.TestCase):
    def test_anthropic_profile_is_selected(self) -> None:
        profile = get_prompt_profile("anthropic")
        self.assertEqual(profile, ANTHROPIC_PROMPT_PROFILE)
        self.assertIn("1800 到 2200", profile.system_prompt)
        self.assertIn("技术", profile.system_prompt)

    def test_unknown_source_falls_back_to_default(self) -> None:
        profile = get_prompt_profile("unknown-site")
        self.assertEqual(profile, DEFAULT_PROMPT_PROFILE)

    def test_build_messages_embeds_source_specific_instructions(self) -> None:
        article = ArticleContent(
            article=DiscoveredArticle(
                source_name="anthropic",
                external_id="a1",
                url="https://example.com",
                title="Test Title",
            ),
            content_text="body",
            content_hash="hash",
        )
        messages = build_summary_messages(article)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("Anthropic", messages[0]["content"])
        payload = json.loads(messages[1]["content"])
        self.assertEqual(payload["source_name"], "anthropic")
        self.assertIn("benchmark", payload["instructions"])


if __name__ == "__main__":
    unittest.main()
