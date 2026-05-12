from __future__ import annotations

import os
import re
import subprocess
from functools import lru_cache
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

from daily_news.config import VideoConfig
from daily_news.models import RenderResult, SummaryResult
from daily_news.utils import ensure_parent, wrap_text


class SimpleVideoRenderer:
    def __init__(self, config: VideoConfig):
        self._config = config

    def render(
        self,
        summary: SummaryResult,
        source_label: str,
        audio_path: Path,
        output_path: Path,
    ) -> RenderResult:
        ensure_parent(output_path)
        cover_path = output_path.with_suffix(".png")
        self._create_cover(summary, source_label, cover_path)
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        trimmed_audio_path = output_path.with_suffix(".audio.m4a")
        self._trim_audio(ffmpeg, audio_path, trimmed_audio_path)
        audio_duration = self._probe_duration(ffmpeg, trimmed_audio_path)
        command = [
            ffmpeg,
            "-y",
            "-loop",
            "1",
            "-framerate",
            str(self._config.fps),
            "-i",
            str(cover_path),
            "-i",
            str(trimmed_audio_path),
            "-t",
            f"{audio_duration:.3f}",
            "-c:v",
            "libx264",
            "-tune",
            "stillimage",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-pix_fmt",
            "yuv420p",
            "-shortest",
            str(output_path),
        ]
        try:
            completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            if completed.returncode != 0:
                raise RuntimeError(f"ffmpeg render failed: {completed.stderr.strip() or completed.stdout.strip()}")
        finally:
            if trimmed_audio_path.exists():
                trimmed_audio_path.unlink()
        return RenderResult(video_path=str(output_path), cover_path=str(cover_path))

    def _create_cover(self, summary: SummaryResult, source_label: str, output_path: Path) -> None:
        ensure_parent(output_path)
        image = Image.new("RGB", (self._config.width, self._config.height), self._config.background_color)
        draw = ImageDraw.Draw(image)
        card_box = (72, 72, self._config.width - 72, self._config.height - 72)
        draw.rounded_rectangle(card_box, radius=28, outline="#334155", width=2, fill="#111827")

        badge_font = _load_font(28, bold=False)
        title_font = _load_font(64, bold=True)
        footer_font = _load_font(22, bold=False)

        draw.text((104, 108), "Anthropic 翻译讲解", fill="#93c5fd", font=badge_font)

        display_text = select_cover_text(summary)
        title_lines = wrap_text(display_text, 16)[:4]
        title_text = "\n".join(title_lines)
        title_bbox = draw.multiline_textbbox((0, 0), title_text, font=title_font, spacing=18, align="center")
        text_width = title_bbox[2] - title_bbox[0]
        text_height = title_bbox[3] - title_bbox[1]
        title_x = (self._config.width - text_width) / 2
        title_y = (self._config.height - text_height) / 2 - 18
        draw.multiline_text(
            (title_x, title_y),
            title_text,
            fill=self._config.text_color,
            font=title_font,
            spacing=18,
            align="center",
        )

        footer = source_label.replace("https://", "").replace("http://", "")
        draw.text((104, self._config.height - 124), footer[:72], fill="#94a3b8", font=footer_font)
        image.save(output_path)

    def _trim_audio(self, ffmpeg: str, audio_path: Path, output_path: Path) -> None:
        command = [
            ffmpeg,
            "-y",
            "-i",
            str(audio_path),
            "-af",
            "silenceremove=stop_periods=-1:stop_duration=0.35:stop_threshold=-45dB,asetpts=N/SR/TB",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(output_path),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        if completed.returncode != 0:
            raise RuntimeError(f"ffmpeg audio trim failed: {completed.stderr.strip() or completed.stdout.strip()}")

    def _probe_duration(self, ffmpeg: str, media_path: Path) -> float:
        completed = subprocess.run(
            [ffmpeg, "-i", str(media_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", completed.stderr)
        if not match:
            raise RuntimeError(f"Unable to determine media duration for {media_path}")
        hours = int(match.group(1))
        minutes = int(match.group(2))
        seconds = float(match.group(3))
        return hours * 3600 + minutes * 60 + seconds


def select_cover_text(summary: SummaryResult) -> str:
    candidate = summary.headline.strip()
    if len(candidate) <= 24:
        return candidate
    for point in summary.key_points:
        normalized = point.strip()
        if 8 <= len(normalized) <= 24:
            return normalized
    return f"{candidate[:21]}..." if len(candidate) > 24 else candidate


def _load_font(size: int, bold: bool) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_path = _find_font_path(bold)
    if font_path is not None:
        return ImageFont.truetype(font_path, size=size)
    return ImageFont.load_default()


@lru_cache(maxsize=2)
def _find_font_path(bold: bool) -> str | None:
    for font_path in _font_candidates(bold):
        if Path(font_path).exists():
            return font_path
    return _fc_match_font_path(bold)


def _font_candidates(bold: bool) -> list[str]:
    windows_candidates = [
        "C:\\Windows\\Fonts\\msyhbd.ttc" if bold else "C:\\Windows\\Fonts\\msyh.ttc",
        "C:\\Windows\\Fonts\\simhei.ttf" if bold else "C:\\Windows\\Fonts\\simsun.ttc",
    ]
    linux_candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansSC-Bold.otf" if bold else "/usr/share/fonts/truetype/noto/NotoSansSC-Regular.otf",
        "/usr/share/fonts/opentype/noto/NotoSansSC-Bold.otf" if bold else "/usr/share/fonts/opentype/noto/NotoSansSC-Regular.otf",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    ]
    macos_candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    if os.name == "nt":
        return windows_candidates + linux_candidates + macos_candidates
    return linux_candidates + macos_candidates + windows_candidates


def _fc_match_font_path(bold: bool) -> str | None:
    style = "Bold" if bold else "Regular"
    font_names = [
        "Noto Sans CJK SC",
        "Noto Sans SC",
        "Source Han Sans SC",
        "WenQuanYi Zen Hei",
        "AR PL UMing CN",
    ]
    for font_name in font_names:
        try:
            completed = subprocess.run(
                ["fc-match", f"{font_name}:style={style}", "-f", "%{file}\n"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
        except FileNotFoundError:
            return None
        if completed.returncode != 0:
            continue
        font_path = completed.stdout.strip()
        if font_path and Path(font_path).exists():
            return font_path
    return None
