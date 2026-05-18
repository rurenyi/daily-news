from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Protocol, TextIO


class ProgressReporter(Protocol):
    def discovery_started(self, limit: int) -> None: ...

    def discovery_completed(self, discovered: int, new: int) -> None: ...

    def run_started(self, total: int, publish_enabled: bool) -> None: ...

    def article_stage(self, index: int, total: int, external_id: str, stage: str, title: str) -> None: ...

    def article_finished(self, index: int, total: int, external_id: str, status: str, title: str) -> None: ...

    def article_failed(self, index: int, total: int, external_id: str, stage: str, error: str, title: str) -> None: ...

    def upload_status(self, message: str) -> None: ...

    def run_completed(self, report: dict) -> None: ...


class NullProgressReporter:
    def discovery_started(self, limit: int) -> None:
        return

    def discovery_completed(self, discovered: int, new: int) -> None:
        return

    def run_started(self, total: int, publish_enabled: bool) -> None:
        return

    def article_stage(self, index: int, total: int, external_id: str, stage: str, title: str) -> None:
        return

    def article_finished(self, index: int, total: int, external_id: str, status: str, title: str) -> None:
        return

    def article_failed(self, index: int, total: int, external_id: str, stage: str, error: str, title: str) -> None:
        return

    def upload_status(self, message: str) -> None:
        return

    def run_completed(self, report: dict) -> None:
        return


@dataclass(slots=True)
class ConsoleProgressReporter:
    stream: TextIO = sys.stderr
    bar_width: int = 24
    _interactive: bool = field(init=False, repr=False)
    _active_line: bool = field(init=False, repr=False)
    _last_line_length: int = field(init=False, repr=False)
    _main_message: str = field(init=False, repr=False)
    _status_message: str = field(init=False, repr=False)
    _status_line_length: int = field(init=False, repr=False)
    _dual_line_mode: bool = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._interactive = hasattr(self.stream, "isatty") and self.stream.isatty()
        self._active_line = False
        self._last_line_length = 0
        self._main_message = ""
        self._status_message = ""
        self._status_line_length = 0
        self._dual_line_mode = False

    def discovery_started(self, limit: int) -> None:
        self._emit(f"[discover] checking latest articles (limit={limit})")

    def discovery_completed(self, discovered: int, new: int) -> None:
        self._emit(f"[discover] found {discovered} article(s), {new} new")

    def run_started(self, total: int, publish_enabled: bool) -> None:
        publish_stage = "on" if publish_enabled else "off"
        self._emit(f"[run] queued {total} article(s), publish={publish_stage}")

    def article_stage(self, index: int, total: int, external_id: str, stage: str, title: str) -> None:
        label = self._format_prefix(index - 1, total)
        self._emit(f"{label} {external_id} -> {stage} | {self._truncate(title, 60)}")

    def article_finished(self, index: int, total: int, external_id: str, status: str, title: str) -> None:
        label = self._format_prefix(index, total)
        self._emit(f"{label} {external_id} -> {status} | {self._truncate(title, 60)}")

    def article_failed(self, index: int, total: int, external_id: str, stage: str, error: str, title: str) -> None:
        label = self._format_prefix(index, total)
        message = f"{label} {external_id} -> failed at {stage} | {self._truncate(title, 60)} | {self._truncate(error, 160)}"
        if self._interactive:
            self._emit_persistent(message)
            return
        self._emit(message)

    def upload_status(self, message: str) -> None:
        if not self._interactive:
            return
        self._status_message = self._truncate(message.strip(), 120)
        self._dual_line_mode = bool(self._status_message)
        self._render_interactive(finalize=False)

    def run_completed(self, report: dict) -> None:
        summary = (
            f"[run] done | discovered={report['discovered']} new={report['new']} "
            f"processed={report['processed']} published={report['published']} failed={report['failed']}"
        )
        self._emit(summary, finalize=True)

    def _format_prefix(self, completed: int, total: int) -> str:
        total = max(total, 1)
        completed = max(0, min(completed, total))
        filled = int(self.bar_width * completed / total)
        bar = "#" * filled + "-" * (self.bar_width - filled)
        return f"[{bar}] {completed}/{total}"

    def _emit(self, message: str, finalize: bool = False) -> None:
        self._main_message = message
        if self._interactive:
            self._render_interactive(finalize=finalize)
            return
        self.stream.write(f"{message}\n")
        self.stream.flush()

    def _emit_persistent(self, message: str) -> None:
        if self._interactive and self._active_line:
            if self._dual_line_mode:
                self.stream.write("\r\x1b[1A\x1b[2K")
                self.stream.write(f"{self._main_message.ljust(self._last_line_length)}\n")
                self.stream.write("\x1b[2K")
                if self._status_message:
                    self.stream.write(f"\x1b[90m{self._status_message.ljust(self._status_line_length)}\x1b[0m")
                self.stream.write("\n")
            else:
                self.stream.write(f"\r{self._main_message.ljust(self._last_line_length)}\n")
            self._active_line = False
            self._last_line_length = 0
            self._status_line_length = 0
            self._dual_line_mode = False
            self._status_message = ""
        self.stream.write(f"{message}\n")
        self.stream.flush()

    def _render_interactive(self, finalize: bool) -> None:
        if self._dual_line_mode:
            if self._active_line:
                self.stream.write("\r\x1b[1A")
            self.stream.write("\x1b[2K")
            main_padded = self._main_message.ljust(self._last_line_length)
            self.stream.write(main_padded)
            self.stream.write("\n\x1b[2K")
            status_padded = self._status_message.ljust(self._status_line_length)
            if status_padded:
                self.stream.write(f"\x1b[90m{status_padded}\x1b[0m")
            self.stream.flush()
            self._last_line_length = len(main_padded)
            self._status_line_length = len(status_padded)
            self._active_line = not finalize
            if finalize:
                self.stream.write("\n")
                self.stream.flush()
                self._active_line = False
                self._last_line_length = 0
                self._status_line_length = 0
                self._dual_line_mode = False
                self._status_message = ""
            return

        padded = self._main_message.ljust(self._last_line_length)
        self.stream.write(f"\r{padded}")
        self.stream.flush()
        self._last_line_length = len(padded)
        self._active_line = True
        if finalize:
            self.stream.write("\n")
            self.stream.flush()
            self._active_line = False
            self._last_line_length = 0

    def _truncate(self, value: str, limit: int) -> str:
        if len(value) <= limit:
            return value
        return f"{value[: limit - 3]}..."
