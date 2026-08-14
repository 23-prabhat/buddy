from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderPreset:
    id: str
    label: str
    base_url: str
    default_model: str
    aliases: tuple[str, ...] = ()
    notes: str = ""


# OpenAI-compatible chat endpoints
PROVIDERS: dict[str, ProviderPreset] = {
    "openai": ProviderPreset(
        id="openai",
        label="OpenAI",
        base_url="",
        default_model="gpt-4o-mini",
        aliases=("oai",),
        notes="Official OpenAI API",
    ),
    "groq": ProviderPreset(
        id="groq",
        label="Groq",
        base_url="https://api.groq.com/openai/v1",
        default_model="llama-3.3-70b-versatile",
        aliases=("gsk",),
        notes="Fast free-tier friendly OpenAI-compatible API",
    ),
    "gemini": ProviderPreset(
        id="gemini",
        label="Google Gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        default_model="gemini-2.0-flash",
        aliases=("google", "google-gemini"),
        notes="Gemini via OpenAI-compatible endpoint",
    ),
    "openrouter": ProviderPreset(
        id="openrouter",
        label="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        default_model="openai/gpt-4o-mini",
        aliases=("or",),
        notes="Many models behind one key",
    ),
    "deepseek": ProviderPreset(
        id="deepseek",
        label="DeepSeek",
        base_url="https://api.deepseek.com",
        default_model="deepseek-chat",
        aliases=(),
        notes="DeepSeek OpenAI-compatible API",
    ),
    "xai": ProviderPreset(
        id="xai",
        label="xAI Grok",
        base_url="https://api.x.ai/v1",
        default_model="grok-2-latest",
        aliases=("grok",),
        notes="xAI Grok API",
    ),
    "nvidia": ProviderPreset(
        id="nvidia",
        label="NVIDIA NIM / Nemotron",
        base_url="https://integrate.api.nvidia.com/v1",
        default_model="nvidia/llama-3.1-nemotron-70b-instruct",
        aliases=("nemotron", "nim"),
        notes="NVIDIA integrate API (Nemotron etc.)",
    ),
    "compatible": ProviderPreset(
        id="compatible",
        label="Custom OpenAI-compatible",
        base_url="",
        default_model="gpt-4o-mini",
        aliases=("custom", "local", "vllm", "ollama"),
        notes="Set AI_BASE_URL yourself (Ollama, vLLM, etc.)",
    ),
    "mock": ProviderPreset(
        id="mock",
        label="Mock (offline)",
        base_url="",
        default_model="mock",
        aliases=("none", "dev"),
        notes="No network — for UI testing",
    ),
}

# Built-in free tier defaults (key comes from FREE_AI_API_KEY / .env)
FREE_PROVIDER_ID = "groq"
FREE_MODEL = "llama-3.3-70b-versatile"


def resolve_provider_id(name: str) -> str | None:
    n = (name or "").strip().lower()
    if not n:
        return None
    if n in PROVIDERS:
        return n
    for pid, preset in PROVIDERS.items():
        if n in preset.aliases or n == preset.label.lower():
            return pid
    return None


def list_providers_help() -> list[str]:
    lines: list[str] = []
    for pid, p in PROVIDERS.items():
        base = p.base_url or "(default OpenAI host / custom)"
        lines.append(f"{pid:<12} {p.label:<22} model={p.default_model}")
        lines.append(f"{'':12} {base}")
    return lines
