from __future__ import annotations

import json
import re
import ssl
from datetime import UTC, datetime
from pathlib import Path
from textwrap import wrap


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def slugify(value: str, limit: int = 80) -> str:
    normalized = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", value.strip(), flags=re.UNICODE)
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-_")
    return (normalized or "item")[:limit]


def compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def strip_markdown_formatting(value: str) -> str:
    text = value.strip()
    text = re.sub(r"```(?:[\w+-]+)?\s*", "", text)
    text = text.replace("```", "")
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s{0,3}[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s{0,3}\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)
    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r"\1", text)
    text = re.sub(r"[*_~`>#]+", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def expand_acronyms_for_tts(value: str) -> str:
    def replacer(match: re.Match[str]) -> str:
        acronym = match.group(1)
        return " ".join(acronym)

    return re.sub(r"(?<![A-Za-z])([A-Z]{2,8})(?![A-Za-z])", replacer, value)


def split_text_for_tts(value: str, target_chars: int = 900, hard_max_chars: int = 1200) -> list[str]:
    text = value.strip()
    if not text:
        return []

    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n{2,}", text) if paragraph.strip()]
    if not paragraphs:
        paragraphs = [text]

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > hard_max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_long_tts_paragraph(paragraph, target_chars=target_chars, hard_max_chars=hard_max_chars))
            continue

        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= hard_max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current)
        current = paragraph

    if current:
        chunks.append(current)
    return chunks


def _split_long_tts_paragraph(value: str, target_chars: int, hard_max_chars: int) -> list[str]:
    sentences = [sentence.strip() for sentence in re.split(r"(?<=[。！？!?；;：:])", value) if sentence.strip()]
    if not sentences:
        sentences = [value]

    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(sentence) > hard_max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_tts_sentence(sentence, hard_max_chars))
            continue

        candidate = f"{current}{sentence}" if current else sentence
        if len(candidate) <= target_chars:
            current = candidate
            continue
        if len(candidate) <= hard_max_chars and current:
            current = candidate
            continue

        if current:
            chunks.append(current)
        current = sentence

    if current:
        chunks.append(current)
    return chunks


def _split_tts_sentence(value: str, hard_max_chars: int) -> list[str]:
    fragments = [fragment.strip() for fragment in re.split(r"(?<=[，,、])", value) if fragment.strip()]
    if not fragments:
        fragments = [value]

    chunks: list[str] = []
    current = ""
    for fragment in fragments:
        candidate = f"{current}{fragment}" if current else fragment
        if len(candidate) <= hard_max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current)

        if len(fragment) <= hard_max_chars:
            current = fragment
            continue

        for index in range(0, len(fragment), hard_max_chars):
            chunks.append(fragment[index : index + hard_max_chars])
        current = ""

    if current:
        chunks.append(current)
    return chunks


def extract_json_object(text: str) -> dict:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?", "", candidate).strip()
        candidate = re.sub(r"```$", "", candidate).strip()
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or start >= end:
        raise ValueError("Model response did not contain a JSON object.")
    return json.loads(candidate[start : end + 1])


def wrap_text(value: str, width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in value.splitlines():
        paragraph = paragraph.strip()
        if not paragraph:
            lines.append("")
            continue
        lines.extend(wrap(paragraph, width=width, break_long_words=True, break_on_hyphens=False))
    return lines or [""]


def httpx_verify_context():
    try:
        import truststore  # type: ignore

        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except Exception:  # noqa: BLE001
        return True
