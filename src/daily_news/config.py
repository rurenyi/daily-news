from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class SourceConfig:
    name: str = "anthropic"
    listing_url: str = "https://www.anthropic.com/news"
    request_timeout_seconds: int = 30


@dataclass(slots=True)
class SummarizerConfig:
    provider: str = "openai_compatible"
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model: str = "qwen-plus"
    api_key_env: str = "DASHSCOPE_API_KEY"


@dataclass(slots=True)
class TTSConfig:
    provider: str = "edge"
    voice: str = "zh-CN-XiaoxiaoNeural"
    rate: str = "+0%"
    volume: str = "+0%"


@dataclass(slots=True)
class VideoConfig:
    width: int = 1280
    height: int = 720
    fps: int = 1
    background_color: str = "#0f172a"
    text_color: str = "#f8fafc"


@dataclass(slots=True)
class BrowserConfig:
    provider: str = "playwright"
    headless: bool = True
    timeout_seconds: int = 45
    save_html: bool = True
    save_pdf: bool = True
    save_screenshot: bool = True
    preferred_channel: str = "msedge"
    storage_state_path: str | None = None


@dataclass(slots=True)
class PublisherConfig:
    enabled: bool = True
    binary: str = "biliup"
    cookies_file: str = "cookies.json"
    title_prefix: str = "Anthropic 研究速读｜"
    title_suffix: str = ""
    copyright: int = 2
    source: str = "https://www.anthropic.com/news"
    tid: int = 171
    tags: list[str] = field(default_factory=lambda: ["AI", "Anthropic", "研究报告"])
    dynamic_template: str = "Anthropic 最新文章中文速读：{title}"
    submit_mode: str = "app"
    upload_line: str | None = None
    concurrent_parts: int = 3


@dataclass(slots=True)
class AppConfig:
    database_path: str = "data\\daily_news.db"
    workspace_dir: str = "data"
    max_articles_per_run: int = 2
    source: SourceConfig = field(default_factory=SourceConfig)
    summarizer: SummarizerConfig = field(default_factory=SummarizerConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    video: VideoConfig = field(default_factory=VideoConfig)
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    publisher: PublisherConfig = field(default_factory=PublisherConfig)

    @property
    def database_file(self) -> Path:
        return Path(self.database_path)

    @property
    def workspace_path(self) -> Path:
        return Path(self.workspace_dir)


def _merge_dataclass(cls, payload: dict | None):
    payload = payload or {}
    return cls(**payload)


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return AppConfig(
        database_path=payload.get("database_path", "data\\daily_news.db"),
        workspace_dir=payload.get("workspace_dir", "data"),
        max_articles_per_run=payload.get("max_articles_per_run", 2),
        source=_merge_dataclass(SourceConfig, payload.get("source")),
        summarizer=_merge_dataclass(SummarizerConfig, payload.get("summarizer")),
        tts=_merge_dataclass(TTSConfig, payload.get("tts")),
        video=_merge_dataclass(VideoConfig, payload.get("video")),
        browser=_merge_dataclass(BrowserConfig, payload.get("browser")),
        publisher=_merge_dataclass(PublisherConfig, payload.get("publisher")),
    )
