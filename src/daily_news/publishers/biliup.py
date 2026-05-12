from __future__ import annotations

from collections.abc import Callable
import re
import shutil
import subprocess
import sys
from pathlib import Path

from daily_news.config import PublisherConfig
from daily_news.models import ArticleContent, PublishResult, SummaryResult
from daily_news.publishers.base import Publisher


class BiliupPublisher(Publisher):
    def __init__(self, config: PublisherConfig):
        self._config = config
        self._binary = _resolve_biliup_binary(config.binary)
        if self._binary is None:
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
        status_callback: Callable[[str], None] | None = None,
    ) -> PublishResult:
        title = self._build_title(summary.headline)
        description = self._build_description(article, summary)
        dynamic = self._config.dynamic_template.format(title=summary.headline)
        command = [
            self._binary,
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
        return_code, output = _run_command_with_live_output(command, status_callback=status_callback)
        if return_code != 0:
            raise RuntimeError(output or "biliup upload failed")
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


def _resolve_biliup_binary(binary: str) -> str | None:
    direct_path = Path(binary)
    if direct_path.exists():
        return str(direct_path)

    which_result = shutil.which(binary)
    if which_result:
        return which_result

    executable_path = Path(sys.executable)
    sibling_candidates = [
        executable_path.with_name(binary),
        executable_path.with_name(f"{binary}.exe"),
    ]
    for candidate in sibling_candidates:
        if candidate.exists():
            return str(candidate)
    return None


def _run_command_with_live_output(
    command: list[str],
    status_callback: Callable[[str], None] | None = None,
) -> tuple[int, str]:
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert process.stdout is not None

    output_lines: list[str] = []
    buffer = ""
    while True:
        chunk = process.stdout.read(1)
        if chunk == "" and process.poll() is not None:
            break
        if chunk == "":
            continue
        if chunk in {"\r", "\n"}:
            line = buffer.strip()
            if line:
                output_lines.append(line)
                if status_callback is not None:
                    status_callback(line)
            buffer = ""
            continue
        buffer += chunk

    if buffer.strip():
        output_lines.append(buffer.strip())
        if status_callback is not None:
            status_callback(buffer.strip())

    return process.wait(), "\n".join(output_lines).strip()
