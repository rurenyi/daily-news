from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from daily_news.config import PublisherConfig
from daily_news.models import ArticleContent, PublishResult, SummaryResult
from daily_news.publishers.base import Publisher


class BiliupPublisher(Publisher):
    def __init__(self, config: PublisherConfig):
        self._config = config
        if not shutil.which(config.binary):
            raise ValueError(
                f"Unable to find biliup executable '{config.binary}'. "
                "Install the package or point publisher.binary to the correct executable."
            )

    def publish(
        self,
        article: ArticleContent,
        summary: SummaryResult,
        video_path: Path,
        cover_path: Path,
    ) -> PublishResult:
        title = self._build_title(summary.headline)
        description = self._build_description(article, summary)
        dynamic = self._config.dynamic_template.format(title=summary.headline)
        command = [
            self._config.binary,
            "--user-cookie",
            self._config.cookies_file,
            "upload",
            str(video_path),
            "--title",
            title,
            "--desc",
            description,
            "--tag",
            ",".join(self._config.tags),
            "--tid",
            str(self._config.tid),
            "--copyright",
            str(self._config.copyright),
            "--source",
            self._config.source or article.article.url,
            "--cover",
            str(cover_path),
            "--dynamic",
            dynamic,
            "--submit",
            self._config.submit_mode,
            "--limit",
            str(self._config.concurrent_parts),
        ]
        if self._config.upload_line:
            command.extend(["--line", self._config.upload_line])
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "biliup upload failed")
        output = completed.stdout.strip() or completed.stderr.strip()
        remote_id = _extract_bvid(output)
        remote_url = f"https://www.bilibili.com/video/{remote_id}" if remote_id else None
        return PublishResult(remote_id=remote_id, remote_url=remote_url, raw_output=output)

    def _build_title(self, headline: str) -> str:
        raw = f"{self._config.title_prefix}{headline}{self._config.title_suffix}".strip()
        return raw[:80]

    def _build_description(self, article: ArticleContent, summary: SummaryResult) -> str:
        points = "\n".join(f"- {point}" for point in summary.key_points[:5])
        body = (
            f"{summary.summary}\n\n"
            f"要点：\n{points}\n\n"
            f"原文标题：{article.article.title}\n"
            f"原文链接：{article.article.url}\n"
        )
        return body[:250]


def _extract_bvid(output: str) -> str | None:
    match = re.search(r"\b(BV[0-9A-Za-z]{10})\b", output)
    if match:
        return match.group(1)
    return None
