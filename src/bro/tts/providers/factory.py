from __future__ import annotations

from bro.core.configuration.settings import Settings
from bro.tts.providers.base import TTSProvider
from bro.tts.providers.mock import MockTTSProvider
from bro.tts.providers.system_tts import SystemTTSProvider


def create_tts_provider(settings: Settings) -> TTSProvider:
    name = (settings.tts_provider or "none").strip().lower()
    if name in ("none", "off", ""):
        return MockTTSProvider()
    if name in ("mock", "dev"):
        return MockTTSProvider()
    if name in ("system", "espeak", "local"):
        return SystemTTSProvider()
    return SystemTTSProvider()
