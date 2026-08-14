from __future__ import annotations

import asyncio

from bro.tts.providers.base import TTSProvider


class MockTTSProvider(TTSProvider):
    name = "mock"

    def __init__(self) -> None:
        self._stopped = False

    async def speak(self, text: str) -> None:
        self._stopped = False
        # Simulate speech duration without audio hardware
        await asyncio.sleep(min(1.5, 0.02 * max(1, len(text.split()))))

    def stop(self) -> None:
        self._stopped = True
