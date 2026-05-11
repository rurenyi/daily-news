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
