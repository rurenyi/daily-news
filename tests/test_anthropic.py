from __future__ import annotations

import unittest
from dataclasses import dataclass

from daily_news.models import DiscoveredArticle
from daily_news.sources.anthropic import parse_article_html, parse_listing_html


LISTING_HTML = """
<html>
  <body>
    <main>
      <a href="/news/claude-design">Introducing Claude Design by Anthropic Labs</a>
      <a href="/news/project-glasswing">Project Glasswing</a>
      <a href="/careers">Careers</a>
    </main>
  </body>
</html>
"""

ARTICLE_HTML = """
<html>
  <head>
    <title>Introducing Claude Design by Anthropic Labs</title>
    <meta name="author" content="Anthropic"/>
  </head>
  <body>
    <main>
      <article>
        <time datetime="2026-04-17">Apr 17, 2026</time>
        <h1>Introducing Claude Design by Anthropic Labs</h1>
        <p>Today, we are launching Claude Design.</p>
        <p>It helps you create polished visual work.</p>
        <p>This is intended to expand collaboration with Claude.</p>
      </article>
    </main>
  </body>
</html>
"""


@dataclass
class FakeCapturedPage:
    url: str
    final_url: str
    title: str
    html: str
    html_path: str | None = None
    pdf_path: str | None = None
    screenshot_path: str | None = None


class AnthropicSourceParsingTests(unittest.TestCase):
    def test_parse_listing_html_filters_news_links(self) -> None:
        articles = parse_listing_html(LISTING_HTML, "https://www.anthropic.com/news", "anthropic-news", "/news/")
        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0].external_id, "claude-design")

    def test_parse_listing_html_supports_research_prefix_and_id_prefix(self) -> None:
        html = """
        <html>
          <body>
            <a href="/research/constitutional-classifiers">Constitutional Classifiers</a>
            <a href="/news/ignore-me">Ignore me</a>
          </body>
        </html>
        """

        articles = parse_listing_html(
            html,
            "https://www.anthropic.com/research",
            "anthropic-research",
            "/research/",
            "research-",
        )

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].external_id, "research-constitutional-classifiers")

    def test_parse_listing_html_prefers_publications_list_on_research_page(self) -> None:
        html = """
        <html>
          <body>
            <main>
              <section>
                <h3>Alignment</h3>
                <a href="/research/alignment">Alignment</a>
              </section>
              <section>
                <h2>Publications</h2>
                <ul>
                  <li>
                    <a href="/research/teaching-claude-why">
                      <span>May 8, 2026</span>
                      <span>Alignment</span>
                      <span>Teaching Claude why</span>
                    </a>
                  </li>
                  <li>
                    <a href="/research/natural-language-autoencoders">
                      <span>May 7, 2026</span>
                      <span>Interpretability</span>
                      <span>Natural Language Autoencoders: Turning Claude’s thoughts into text</span>
                    </a>
                  </li>
                </ul>
              </section>
            </main>
          </body>
        </html>
        """

        articles = parse_listing_html(
            html,
            "https://www.anthropic.com/research",
            "anthropic-research",
            "/research/",
            "research-",
        )

        self.assertEqual([article.external_id for article in articles[:2]], [
            "research-teaching-claude-why",
            "research-natural-language-autoencoders",
        ])
        self.assertEqual(articles[0].title, "Teaching Claude why")
        self.assertEqual(
            articles[1].title,
            "Natural Language Autoencoders: Turning Claude’s thoughts into text",
        )

    def test_parse_article_html_extracts_body(self) -> None:
        discovered = DiscoveredArticle(
            source_name="anthropic",
            external_id="claude-design",
            url="https://www.anthropic.com/news/claude-design",
            title="Placeholder",
        )
        content = parse_article_html(
            ARTICLE_HTML,
            discovered,
            FakeCapturedPage(
                url=discovered.url,
                final_url=discovered.url,
                title="Introducing Claude Design by Anthropic Labs",
                html=ARTICLE_HTML,
                html_path="page.html",
                pdf_path="page.pdf",
                screenshot_path="page.png",
            ),
        )
        self.assertIn("Claude Design", content.article.title)
        self.assertIn("create polished visual work", content.content_text)
        self.assertEqual(content.article.published_at, "2026-04-17")
        self.assertEqual(content.page_pdf_path, "page.pdf")


if __name__ == "__main__":
    unittest.main()
