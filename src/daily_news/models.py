from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class DiscoveredArticle:
    source_name: str
    external_id: str
    url: str
    title: str
    published_at: str | None = None
    author: str | None = None


@dataclass(slots=True)
class ArticleContent:
    article: DiscoveredArticle
    content_text: str
    content_hash: str
    page_html_path: str | None = None
    page_pdf_path: str | None = None
    page_screenshot_path: str | None = None


@dataclass(slots=True)
class SummaryResult:
    headline: str
    summary: str
    key_points: list[str]
    script: str

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class RenderResult:
    video_path: str
    cover_path: str


@dataclass(slots=True)
class PublishResult:
    remote_id: str | None
    remote_url: str | None
    raw_output: str
