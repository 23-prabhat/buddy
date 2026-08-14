from __future__ import annotations

from bro.audio.stt.base import SpeechToTextProvider
from bro.audio.stt.mock import MockSTTProvider
from bro.core.configuration.settings import Settings


def create_stt_provider(settings: Settings) -> SpeechToTextProvider:
    name = (settings.stt_provider or "none").strip().lower()
    if name in ("none", "mock", "dev", ""):
        return MockSTTProvider()
    if name in ("openai", "whisper", "openai-whisper"):
        from bro.audio.stt.openai_whisper import OpenAIWhisperSTT

        base = settings.ai_base_url.strip() or None
        return OpenAIWhisperSTT(
            api_key=settings.ai_api_key,
            model=settings.stt_model or "whisper-1",
            base_url=base,
        )
    raise ValueError(f"Unknown STT_PROVIDER: {settings.stt_provider}")
