from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Browser, Error, Page, Playwright, sync_playwright

from daily_news.browser.base import BrowserCapture, CapturedPage
from daily_news.config import BrowserConfig
from daily_news.utils import ensure_parent


class PlaywrightBrowserCapture(BrowserCapture):
    def __init__(self, config: BrowserConfig):
        self._config = config
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    def capture(self, url: str, artifact_dir: Path, artifact_stem: str) -> CapturedPage:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        browser = self._get_browser()
        context_args: dict = {
            "viewport": {"width": 1440, "height": 1200},
        }
        if self._config.storage_state_path:
            context_args["storage_state"] = self._config.storage_state_path
        context = browser.new_context(**context_args)
        try:
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=self._config.timeout_seconds * 1000)
            page.wait_for_load_state("networkidle", timeout=self._config.timeout_seconds * 1000)
            self._warm_page(page)
            final_url = page.url
            title = page.title()
            html = page.content()
            html_path = None
            pdf_path = None
            screenshot_path = None

            if self._config.save_html:
                html_file = artifact_dir / f"{artifact_stem}.html"
                ensure_parent(html_file)
                html_file.write_text(html, encoding="utf-8")
                html_path = str(html_file)
            if self._config.save_pdf:
                pdf_file = artifact_dir / f"{artifact_stem}.pdf"
                page.pdf(path=str(pdf_file), print_background=True, format="A4")
                pdf_path = str(pdf_file)
            if self._config.save_screenshot:
                screenshot_file = artifact_dir / f"{artifact_stem}.png"
                page.screenshot(path=str(screenshot_file), full_page=True)
                screenshot_path = str(screenshot_file)

            return CapturedPage(
                url=url,
                final_url=final_url,
                title=title,
                html=html,
                html_path=html_path,
                pdf_path=pdf_path,
                screenshot_path=screenshot_path,
            )
        finally:
            context.close()

    def close(self) -> None:
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

    def _get_browser(self) -> Browser:
        if self._browser is None:
            self._playwright = sync_playwright().start()
            self._browser = self._launch_browser()
        return self._browser

    def _launch_browser(self) -> Browser:
        assert self._playwright is not None
        launch_candidates: list[dict] = []
        if self._config.preferred_channel:
            launch_candidates.append({"channel": self._config.preferred_channel})
        launch_candidates.extend(
            [
                {"channel": "chrome"},
                {"channel": "msedge"},
                {"executable_path": r"C:\Program Files\Google\Chrome\Application\chrome.exe"},
                {"executable_path": r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"},
                {"executable_path": r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"},
                {"executable_path": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"},
                {},
            ]
        )
        errors: list[str] = []
        for candidate in launch_candidates:
            try:
                return self._playwright.chromium.launch(headless=self._config.headless, **candidate)
            except Error as exc:
                label = candidate.get("channel") or candidate.get("executable_path") or "bundled-chromium"
                errors.append(f"{label}: {exc}")
        raise RuntimeError(
            "Unable to launch a Chromium browser for Playwright capture. "
            "Tried system channels and bundled Chromium. "
            + " | ".join(errors)
        )

    def _warm_page(self, page: Page) -> None:
        page.evaluate(
            """
            async () => {
              const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
              for (let i = 0; i < 4; i++) {
                window.scrollTo(0, document.body.scrollHeight);
                await delay(350);
              }
              window.scrollTo(0, 0);
            }
            """
        )
