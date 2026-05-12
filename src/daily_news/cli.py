from __future__ import annotations

import argparse
import json

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
            print(json.dumps(rows, ensure_ascii=False, indent=2))
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


if __name__ == "__main__":
    main()
