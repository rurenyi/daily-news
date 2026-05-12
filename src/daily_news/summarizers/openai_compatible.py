from __future__ import annotations

import json
import os

import httpx

from daily_news.config import SummarizerConfig
from daily_news.models import ArticleContent, SummaryResult
from daily_news.summarizers.base import Summarizer
from daily_news.summarizers.prompts import build_summary_messages
from daily_news.utils import extract_json_object, httpx_verify_context, strip_markdown_formatting


class OpenAICompatibleSummarizer(Summarizer):
    def __init__(self, config: SummarizerConfig):
        self._config = config
        api_key = os.environ.get(config.api_key_env)
        if not api_key:
            raise ValueError(
                f"Missing API key environment variable: {config.api_key_env}. "
                "Set it or use the mock summarizer for local testing."
            )
        self._api_key = api_key
        self._client = httpx.Client(timeout=90, verify=httpx_verify_context())

    def summarize(self, article: ArticleContent) -> SummaryResult:
        response = self._client.post(
            f"{self._config.base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self._config.model,
                "temperature": 0.3,
                "messages": build_summary_messages(article),
            },
        )
        response.raise_for_status()
        payload = response.json()
        message = payload["choices"][0]["message"]["content"]
        data = extract_json_object(message)
        key_points = [strip_markdown_formatting(str(item)) for item in data.get("key_points", []) if str(item).strip()]
        key_points = [item for item in key_points if item]
        if not key_points:
            raise ValueError("Model response did not include key_points.")
        headline = strip_markdown_formatting(str(data["headline"]))
        summary = strip_markdown_formatting(str(data["summary"]))
        script = strip_markdown_formatting(str(data.get("script", "")))
        if not script:
            script = f"{headline}。{summary}。重点包括：{'；'.join(key_points)}。"
        return SummaryResult(
            headline=headline,
            summary=summary,
            key_points=key_points,
            script=script,
        )
