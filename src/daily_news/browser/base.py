from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class CapturedPage:
    url: str
    final_url: str
    title: str
    html: str
    html_path: str | None = None
    pdf_path: str | None = None
    screenshot_path: str | None = None


class BrowserCapture(ABC):
    @abstractmethod
    def capture(self, url: str, artifact_dir: Path, artifact_stem: str) -> CapturedPage:
        raise NotImplementedError

    def close(self) -> None:
        return None
