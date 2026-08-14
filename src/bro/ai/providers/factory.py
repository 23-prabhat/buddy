from __future__ import annotations

from bro.ai.providers.base import AIProvider
from bro.ai.providers.catalog import (
    FREE_MODEL,
    FREE_PROVIDER_ID,
    PROVIDERS,
    resolve_provider_id,
)
from bro.ai.providers.mock import MockAIProvider
from bro.ai.providers.openai_compatible import OpenAICompatibleProvider
from bro.core.configuration.settings import Settings


def _effective_credentials(settings: Settings) -> tuple[str, str, str, str]:
    """Return (provider_id, model, api_key, base_url)."""
    mode = (settings.ai_key_mode or "free").strip().lower()
    if mode in ("mock", "none", "dev", "off"):
        return "mock", "mock", "", ""

    if mode in ("free", "builtin", "default"):
        free_pid = resolve_provider_id(settings.free_ai_provider) or FREE_PROVIDER_ID
        preset = PROVIDERS.get(free_pid, PROVIDERS[FREE_PROVIDER_ID])
        key = (settings.free_ai_api_key or "").strip()
        model = (settings.free_ai_model or FREE_MODEL).strip() or FREE_MODEL
        return preset.id, model, key, preset.base_url

    # own key mode
    raw = (settings.ai_provider or "openai").strip().lower()
    pid = resolve_provider_id(raw) or raw
    if pid in ("mock", "none", "dev"):
        return "mock", "mock", "", ""

    preset = PROVIDERS.get(pid)
    if preset is None:
        base = (settings.ai_base_url or "").strip()
        key = (settings.ai_api_key or "").strip()
        model = (settings.ai_model or "gpt-4o-mini").strip()
        return "compatible", model, key, base

    if pid == "mock":
        return "mock", "mock", "", ""

    key = (settings.ai_api_key or "").strip()
    model = (settings.ai_model or "").strip() or preset.default_model
    base = (settings.ai_base_url or "").strip() or preset.base_url
    return pid, model, key, base


def create_ai_provider(settings: Settings) -> AIProvider:
    pid, model, key, base = _effective_credentials(settings)
    if pid == "mock":
        return MockAIProvider()

    if not key:
        mode = (settings.ai_key_mode or "free").lower()
        if mode in ("free", "builtin", "default"):
            raise ValueError(
                "Free API key missing. Set FREE_AI_API_KEY in .env or run: apikey free"
            )
        raise ValueError(
            "No API key set. Run: apikey set <your-key>   or   apikey free"
        )

    return OpenAICompatibleProvider(
        api_key=key,
        model=model,
        base_url=base or None,
        provider_label=pid,
    )


def describe_ai_config(settings: Settings) -> dict[str, str]:
    pid, model, key, base = _effective_credentials(settings)
    mode = (settings.ai_key_mode or "free").strip().lower()
    preview = "missing"
    if key:
        preview = f"{key[:6]}…{key[-4:]}" if len(key) > 12 else "set"
    return {
        "key_mode": mode,
        "provider": pid,
        "model": model,
        "base_url": base or "(default)",
        "api_key": "set" if key else "missing",
        "api_key_preview": preview,
    }
