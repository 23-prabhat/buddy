from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ResponseStyle = Literal["concise", "balanced", "detailed", "technical"]
AppMode = Literal["general", "meeting", "screen", "meeting+screen", "coding", "study"]
KeyMode = Literal["free", "own", "mock"]


def _default_env_files() -> tuple[str, ...]:
    from bro.core.configuration.envfile import project_env_path

    paths = [str(project_env_path()), ".env"]
    seen: set[str] = set()
    out: list[str] = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            out.append(path)
    return tuple(out)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_default_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # free = built-in free Groq key; own = user-provided key; mock = offline
    ai_key_mode: str = Field(default="free", alias="AI_KEY_MODE")
    ai_provider: str = Field(default="groq", alias="AI_PROVIDER")
    ai_model: str = Field(default="llama-3.3-70b-versatile", alias="AI_MODEL")
    ai_api_key: str = Field(default="", alias="AI_API_KEY")
    ai_base_url: str = Field(default="", alias="AI_BASE_URL")
    # Built-in free tier key (set in .env — never commit real keys to git)
    free_ai_api_key: str = Field(default="", alias="FREE_AI_API_KEY")
    free_ai_provider: str = Field(default="groq", alias="FREE_AI_PROVIDER")
    free_ai_model: str = Field(default="llama-3.3-70b-versatile", alias="FREE_AI_MODEL")

    stt_provider: str = Field(default="mock", alias="STT_PROVIDER")
    stt_model: str = Field(default="whisper-1", alias="STT_MODEL")

    tts_provider: str = Field(default="none", alias="TTS_PROVIDER")
    tts_model: str = Field(default="", alias="TTS_MODEL")
    voice_output_enabled: bool = Field(default=False, alias="VOICE_OUTPUT_ENABLED")

    meeting_context_seconds: int = Field(default=120, alias="MEETING_CONTEXT_SECONDS")
    meeting_auto_answer: bool = Field(default=True, alias="MEETING_AUTO_ANSWER")

    screen_capture_enabled: bool = Field(default=True, alias="SCREEN_CAPTURE_ENABLED")
    screen_monitor: int = Field(default=1, alias="SCREEN_MONITOR")
    screen_force_vision: bool = Field(default=False, alias="SCREEN_FORCE_VISION")
    ocr_lang: str = Field(default="eng", alias="OCR_LANG")

    audio_sample_rate: int = Field(default=16000, alias="AUDIO_SAMPLE_RATE")
    audio_device: str = Field(default="", alias="AUDIO_DEVICE")

    hotkeys_enabled: bool = Field(default=True, alias="HOTKEYS_ENABLED")
    rag_enabled: bool = Field(default=True, alias="RAG_ENABLED")
    rag_path: str = Field(default="", alias="RAG_PATH")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    response_style: ResponseStyle = Field(default="balanced", alias="RESPONSE_STYLE")
    mode: AppMode = Field(default="general", alias="APP_MODE")

    def public_dict(self) -> dict[str, str | int | bool]:
        from bro.ai.providers.factory import describe_ai_config

        ai = describe_ai_config(self)
        return {
            "ai_key_mode": ai["key_mode"],
            "ai_provider": ai["provider"],
            "ai_model": ai["model"],
            "ai_base_url": ai["base_url"],
            "ai_api_key": ai["api_key"],
            "ai_api_key_preview": ai["api_key_preview"],
            "stt_provider": self.stt_provider,
            "stt_model": self.stt_model,
            "tts_provider": self.tts_provider,
            "voice_output_enabled": self.voice_output_enabled,
            "meeting_context_seconds": self.meeting_context_seconds,
            "meeting_auto_answer": self.meeting_auto_answer,
            "screen_capture_enabled": self.screen_capture_enabled,
            "screen_monitor": self.screen_monitor,
            "screen_force_vision": self.screen_force_vision,
            "ocr_lang": self.ocr_lang,
            "audio_sample_rate": self.audio_sample_rate,
            "hotkeys_enabled": self.hotkeys_enabled,
            "rag_enabled": self.rag_enabled,
            "rag_path": self.rag_path or "(none)",
            "response_style": self.response_style,
            "mode": self.mode,
            "log_level": self.log_level,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reload_settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()
