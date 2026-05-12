from __future__ import annotations

import argparse
import json
from collections.abc import Iterable

from daily_news.browser.playwright_capture import PlaywrightBrowserCapture
from daily_news.config import AppConfig, load_config
from daily_news.pipeline import DailyNewsPipeline
from daily_news.progress import ConsoleProgressReporter
from daily_news.publishers.base import NullPublisher
from daily_news.publishers.biliup import BiliupPublisher
from daily_news.sources.anthropic import AnthropicNewsSource
from daily_news.sources.composite import CompositeSourceAdapter
from daily_news.storage.sqlite_store import SqliteArticleStore
from daily_news.summarizers.mock import MockSummarizer
from daily_news.summarizers.openai_compatible import OpenAICompatibleSummarizer
from daily_news.tts.edge import EdgeTTS
from daily_news.video.simple_renderer import SimpleVideoRenderer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="daily-news")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in ("discover", "run-once", "list"):
        subparser = subparsers.add_parser(name)
        subparser.add_argument("--config", default="config.example.json")
        if name in {"discover", "run-once"}:
            subparser.add_argument("--limit", type=int, default=None)
        if name == "run-once":
            subparser.add_argument("--skip-publish", action="store_true")
        if name == "list":
            subparser.add_argument("--json", action="store_true")
    serve_parser = subparsers.add_parser("serve")
    serve_parser.add_argument("--config", default="config.example.json")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config = load_config(args.config)
    if args.command == "serve":
        import uvicorn

        from daily_news.web.app import create_app

        uvicorn.run(create_app(config), host=args.host, port=args.port)
        return
    if args.command == "list":
        store = SqliteArticleStore(config.database_file)
        try:
            rows = [
                {
                    "external_id": row["external_id"],
                    "title": row["title"],
                    "status": row["status"],
                    "url": row["url"],
                    "published_video_url": row["published_video_url"],
                    "updated_at": row["updated_at"],
                }
                for row in store.list_articles()
            ]
            if args.json:
                print(json.dumps(rows, ensure_ascii=False, indent=2))
            else:
                print(format_article_table(rows))
            return
        finally:
            store.close()

    skip_publish = args.command != "run-once" or getattr(args, "skip_publish", False)
    pipeline, store = build_pipeline(config, skip_publish=skip_publish)
    progress = ConsoleProgressReporter()
    try:
        if args.command == "discover":
            print(json.dumps(pipeline.discover(args.limit, progress=progress), ensure_ascii=False, indent=2))
            return
        if args.command == "run-once":
            print(json.dumps(pipeline.run_once(args.limit, progress=progress), ensure_ascii=False, indent=2))
            return
        parser.error(f"Unsupported command: {args.command}")
    finally:
        pipeline.close()
        store.close()


def build_pipeline(config: AppConfig, skip_publish: bool) -> tuple[DailyNewsPipeline, SqliteArticleStore]:
    config.workspace_path.mkdir(parents=True, exist_ok=True)
    store = SqliteArticleStore(config.database_file)
    source = _build_source(config)
    summarizer = _build_summarizer(config)
    tts = EdgeTTS(config.tts)
    renderer = SimpleVideoRenderer(config.video)
    if skip_publish:
        config.publisher.enabled = False
    publisher = NullPublisher() if not config.publisher.enabled else BiliupPublisher(config.publisher)
    return DailyNewsPipeline(config, store, source, summarizer, tts, renderer, publisher), store


def _build_source(config: AppConfig):
    sources = []
    for source_config in config.enabled_sources:
        if source_config.provider != "anthropic":
            raise ValueError(f"Unsupported source provider: {source_config.provider}")
        sources.append(AnthropicNewsSource(source_config, PlaywrightBrowserCapture(config.browser), config.workspace_path))
    if not sources:
        raise ValueError("At least one source must be enabled.")
    if len(sources) == 1:
        return sources[0]
    return CompositeSourceAdapter(sources)


def _build_summarizer(config: AppConfig):
    if config.summarizer.provider == "mock":
        return MockSummarizer()
    if config.summarizer.provider == "openai_compatible":
        return OpenAICompatibleSummarizer(config.summarizer)
    raise ValueError(f"Unsupported summarizer provider: {config.summarizer.provider}")


def format_article_table(rows: Iterable[dict]) -> str:
    data = list(rows)
    if not data:
        return "No local article records."

    headers = {
        "updated_at": "Updated",
        "status": "Status",
        "title": "Title",
        "url": "URL",
    }
    max_widths = {
        "updated_at": 25,
        "status": 18,
        "title": 48,
        "url": 88,
    }
    columns = ["updated_at", "status", "title", "url"]

    rendered_rows: list[dict[str, str]] = []
    widths = {column: len(headers[column]) for column in columns}
    for row in data:
        rendered = {column: _truncate_table_value(str(row.get(column, "") or ""), max_widths[column]) for column in columns}
        rendered_rows.append(rendered)
        for column in columns:
            widths[column] = max(widths[column], len(rendered[column]))

    header_line = " | ".join(headers[column].ljust(widths[column]) for column in columns)
    separator_line = "-+-".join("-" * widths[column] for column in columns)
    body_lines = [
        " | ".join(rendered[column].ljust(widths[column]) for column in columns)
        for rendered in rendered_rows
    ]
    return "\n".join([header_line, separator_line, *body_lines])


def _truncate_table_value(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    if limit <= 3:
        return value[:limit]
    return f"{value[: limit - 3]}..."


if __name__ == "__main__":
    main()
