from __future__ import annotations

import hashlib
import json
import re
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from daily_news.browser.base import BrowserCapture, CapturedPage
from daily_news.config import SourceConfig
from daily_news.models import ArticleContent, DiscoveredArticle
from daily_news.sources.base import SourceAdapter
from daily_news.utils import compact_text


def parse_listing_html(
    html: str,
    listing_url: str,
    source_name: str,
    article_path_prefix: str,
    id_prefix: str = "",
) -> list[DiscoveredArticle]:
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    results: list[DiscoveredArticle] = []
    for anchor in _iter_listing_anchors(soup, article_path_prefix):
        href = anchor.get("href", "").strip()
        if not href:
            continue
        full_url = urljoin(listing_url, href)
        parsed = urlparse(full_url)
        if article_path_prefix not in parsed.path:
            continue
        if full_url.rstrip("/") == listing_url.rstrip("/"):
            continue
        if full_url in seen:
            continue
        title = _extract_listing_title(anchor)
        if len(title) < 8:
            continue
        article_id = parsed.path.rstrip("/").split("/")[-1]
        external_id = f"{id_prefix}{article_id}"
        seen.add(full_url)
        results.append(
            DiscoveredArticle(
                source_name=source_name,
                external_id=external_id,
                url=full_url,
                title=title,
            )
        )
    return results


def _iter_listing_anchors(soup: BeautifulSoup, article_path_prefix: str):
    publications_anchors = _find_publications_anchors(soup, article_path_prefix)
    if publications_anchors:
        return publications_anchors
    return soup.select("a[href]")


def _find_publications_anchors(soup: BeautifulSoup, article_path_prefix: str) -> list:
    heading = soup.find(lambda tag: compact_text(tag.get_text(" ", strip=True)).lower() == "publications")
    if heading is None:
        return []

    section = heading.find_parent("section")
    if section is None:
        return []

    return [
        anchor
        for anchor in section.select("a[href]")
        if article_path_prefix in urlparse(urljoin("https://www.anthropic.com", anchor.get("href", ""))).path
    ]


def _extract_listing_title(anchor) -> str:
    heading = anchor.select_one("h1, h2, h3, h4, h5, h6, [role='heading']")
    if heading is not None:
        return compact_text(" ".join(heading.stripped_strings))

    text_parts = [compact_text(part) for part in anchor.stripped_strings]
    text_parts = [part for part in text_parts if part]
    if not text_parts:
        return ""
    return text_parts[-1]


def parse_article_html(
    html: str,
    article: DiscoveredArticle,
    captured_page: CapturedPage | None = None,
) -> ArticleContent:
    soup = BeautifulSoup(html, "html.parser")
    title = _extract_title(soup) or (captured_page.title if captured_page else None) or article.title
    published_at = _extract_published_at(soup)
    author = _extract_author(soup)
    content_text = _extract_content_text(soup)
    updated_article = DiscoveredArticle(
        source_name=article.source_name,
        external_id=article.external_id,
        url=article.url,
        title=title,
        published_at=published_at or article.published_at,
        author=author or article.author,
    )
    content_hash = hashlib.sha256(content_text.encode("utf-8")).hexdigest()
    return ArticleContent(
        article=updated_article,
        content_text=content_text,
        content_hash=content_hash,
        page_html_path=captured_page.html_path if captured_page else None,
        page_pdf_path=captured_page.pdf_path if captured_page else None,
        page_screenshot_path=captured_page.screenshot_path if captured_page else None,
    )


class AnthropicNewsSource(SourceAdapter):
    def __init__(self, config: SourceConfig, browser_capture: BrowserCapture, workspace_path: Path):
        self._config = config
        self._browser_capture = browser_capture
        self._capture_root = workspace_path / "captures" / config.name
        self.name = config.name

    def discover(self, limit: int) -> list[DiscoveredArticle]:
        listing_capture = self._browser_capture.capture(
            url=self._config.listing_url,
            artifact_dir=self._capture_root / "_listing",
            artifact_stem="listing",
        )
        articles = parse_listing_html(
            listing_capture.html,
            self._config.listing_url,
            self._config.name,
            self._config.article_path_prefix,
            self._config.id_prefix,
        )
        return articles[:limit]

    def fetch(self, article: DiscoveredArticle) -> ArticleContent:
        article_capture = self._browser_capture.capture(
            url=article.url,
            artifact_dir=self._capture_root / article.external_id,
            artifact_stem=article.external_id,
        )
        return parse_article_html(article_capture.html, article, article_capture)

    def close(self) -> None:
        self._browser_capture.close()


def _extract_title(soup: BeautifulSoup) -> str | None:
    selectors = ["h1", "meta[property='og:title']", "title"]
    for selector in selectors:
        node = soup.select_one(selector)
        if not node:
            continue
        if node.name == "meta":
            content = node.get("content")
        else:
            content = node.get_text(" ", strip=True)
        if content:
            return compact_text(unescape(content))
    return None


def _extract_published_at(soup: BeautifulSoup) -> str | None:
    time_tag = soup.select_one("time[datetime]")
    if time_tag and time_tag.get("datetime"):
        return time_tag["datetime"].strip()
    page_text = compact_text(soup.get_text(" ", strip=True))
    match = re.search(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}\b", page_text)
    if match:
        return match.group(0)
    for script in soup.select("script[type='application/ld+json']"):
        raw = script.string or script.get_text()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        candidates = payload if isinstance(payload, list) else [payload]
        for item in candidates:
            if isinstance(item, dict) and item.get("datePublished"):
                return str(item["datePublished"])
    return None


def _extract_author(soup: BeautifulSoup) -> str | None:
    meta = soup.select_one("meta[name='author']")
    if meta and meta.get("content"):
        return compact_text(meta["content"])
    return None


def _extract_content_text(soup: BeautifulSoup) -> str:
    container = soup.select_one("article") or soup.select_one("main") or soup.body
    if container is None:
        raise ValueError("Unable to locate article content container.")

    for selector in ["script", "style", "noscript", "svg", "button", "nav", "footer", "form"]:
        for node in container.select(selector):
            node.decompose()

    paragraphs: list[str] = []
    for node in container.select("h1, h2, h3, p, li, blockquote"):
        text = compact_text(node.get_text(" ", strip=True))
        if text and text not in paragraphs:
            paragraphs.append(text)
    if len(paragraphs) < 3:
        text = compact_text(container.get_text("\n", strip=True))
        if not text:
            raise ValueError("Extracted article content was empty.")
        return text
    return "\n".join(paragraphs)
