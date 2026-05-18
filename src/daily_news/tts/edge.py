from __future__ import annotations

import asyncio
import os
import tempfile
import threading
from pathlib import Path

import aiohttp
import edge_tts
import edge_tts.communicate as edge_communicate
import edge_tts.voices as edge_voices

from daily_news.config import TTSConfig
from daily_news.tts.base import TextToSpeech
from daily_news.utils import (
    ensure_parent,
    expand_acronyms_for_tts,
    httpx_verify_context,
    split_text_for_tts,
    strip_markdown_formatting,
)


class EdgeTTS(TextToSpeech):
    def __init__(self, config: TTSConfig):
        self._config = config

    def synthesize(self, text: str, output_path: Path) -> None:
        ensure_parent(output_path)
        text = strip_markdown_formatting(text)
        text = expand_acronyms_for_tts(text)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self._save(text, output_path))
            return

        error: Exception | None = None

        def runner() -> None:
            nonlocal error
            try:
                asyncio.run(self._save(text, output_path))
            except Exception as exc:  # noqa: BLE001
                error = exc

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        thread.join()
        if error is not None:
            raise error

    async def _save(self, text: str, output_path: Path) -> None:
        chunks = split_text_for_tts(text)
        if not chunks:
            raise ValueError("TTS input text was empty after preprocessing.")
        ssl_context = httpx_verify_context()
        edge_communicate._SSL_CTX = ssl_context
        edge_voices._SSL_CTX = ssl_context
        if len(chunks) == 1:
            await self._save_chunk(chunks[0], output_path, ssl_context)
            return

        with tempfile.TemporaryDirectory() as temp_dir:
            part_paths: list[Path] = []
            for index, chunk in enumerate(chunks, start=1):
                part_path = Path(temp_dir) / f"part-{index:03d}.mp3"
                await self._save_chunk(chunk, part_path, ssl_context)
                part_paths.append(part_path)
            with output_path.open("wb") as merged:
                for part_path in part_paths:
                    merged.write(part_path.read_bytes())

    async def _save_chunk(self, text: str, output_path: Path, ssl_context) -> None:
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        try:
            communicator = edge_tts.Communicate(
                text=text,
                voice=self._config.voice,
                rate=self._config.rate,
                volume=self._config.volume,
                connector=connector,
                proxy=os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY"),
            )
            await communicator.save(str(output_path))
        finally:
            await connector.close()
