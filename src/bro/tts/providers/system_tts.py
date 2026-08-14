from __future__ import annotations

import asyncio
import shutil
import subprocess
import tempfile
from pathlib import Path

from bro.tts.providers.base import TTSProvider


class SystemTTSProvider(TTSProvider):
    """Use espeak/espeak-ng or spd-say when available; else no-op with message."""

    name = "system"

    def __init__(self) -> None:
        self._proc: subprocess.Popen | None = None

    def _bin(self) -> str | None:
        for name in ("espeak-ng", "espeak", "spd-say", "say"):
            if shutil.which(name):
                return name
        return None

    async def speak(self, text: str) -> None:
        self.stop()
        binary = self._bin()
        if not binary:
            return
        clean = text.strip()[:2000]
        if not clean:
            return

        def run() -> None:
            if binary in ("espeak-ng", "espeak"):
                self._proc = subprocess.Popen(
                    [binary, clean],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            elif binary == "spd-say":
                self._proc = subprocess.Popen(
                    [binary, clean],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:  # macOS say
                self._proc = subprocess.Popen(
                    [binary, clean],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            if self._proc:
                self._proc.wait()

        await asyncio.to_thread(run)

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
            except Exception:  # noqa: BLE001
                pass
        self._proc = None
