from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase


@dataclass(frozen=True, slots=True)
class ProviderPreset:
    id: str
    label: str
    base_url: str
    default_model: str
    aliases: tuple[str, ...] = ()
    notes: str = ""
    # Glob patterns of known model-name patterns that accept image input.
    # Empty tuple => no known vision-capable models for this provider.
    vision_models: tuple[str, ...] = ()


# OpenAI-compatible chat endpoints
PROVIDERS: dict[str, ProviderPreset] = {
    "openai": ProviderPreset(
        id="openai",
        label="OpenAI",
        base_url="",
        default_model="gpt-4o-mini",
        aliases=("oai",),
        notes="Official OpenAI API",
        vision_models=("gpt-4o*", "gpt-4-turbo*", "gpt-4-vision*"),
    ),
    "groq": ProviderPreset(
        id="groq",
        label="Groq",
        base_url="https://api.groq.com/openai/v1",
        default_model="llama-3.3-70b-versatile",
        aliases=("gsk",),
        notes="Fast free-tier friendly OpenAI-compatible API",
        # Groq's OpenAI-compatible vision models are Llama 4 and Llama 3.2 vision.
        vision_models=(
            "meta-llama/llama-4-*",
            "meta-llama/llama-3.2-*vision*",
            "llama-3.2-*vision*",
            "llama-4-*",
            "*llava*",
        ),
    ),
    "gemini": ProviderPreset(
        id="gemini",
        label="Google Gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        default_model="gemini-2.0-flash",
        aliases=("google", "google-gemini"),
        notes="Gemini via OpenAI-compatible endpoint",
        vision_models=("gemini-*flash*", "gemini-*pro*", "gemini-*ultra*"),
    ),
    "openrouter": ProviderPreset(
        id="openrouter",
        label="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        default_model="openai/gpt-4o-mini",
        aliases=("or",),
        notes="Many models behind one key",
        # OpenRouter routes are namespaced ("vendor/model"); the trailing glob
        # catches any of those names regardless of vendor prefix.
        vision_models=(
            "*gpt-4o*",
            "*gpt-4-turbo*",
            "*gpt-4-vision*",
            "*claude-3*",
            "*claude-4*",
            "*gemini-*flash*",
            "*gemini-*pro*",
            "*llama-4-*",
            "*llava*",
            "*qwen*vl*",
            "*pixtral*",
            "*internvl*",
            "*glm-4v*",
        ),
    ),
    "deepseek": ProviderPreset(
        id="deepseek",
        label="DeepSeek",
        base_url="https://api.deepseek.com",
        default_model="deepseek-chat",
        aliases=(),
        notes="DeepSeek OpenAI-compatible API (text-only via chat endpoint)",
    ),
    "xai": ProviderPreset(
        id="xai",
        label="xAI Grok",
        base_url="https://api.x.ai/v1",
        default_model="grok-2-latest",
        aliases=("grok",),
        notes="xAI Grok API",
        vision_models=("grok-2-vision*", "grok-vision*", "*grok-*-vision*"),
    ),
    "nvidia": ProviderPreset(
        id="nvidia",
        label="NVIDIA NIM / Nemotron",
        base_url="https://integrate.api.nvidia.com/v1",
        default_model="nvidia/llama-3.1-nemotron-70b-instruct",
        aliases=("nemotron", "nim"),
        notes="NVIDIA integrate API (Nemotron etc.)",
        # NVIDIA's NIM catalog includes Llama 3.2 vision, VILA, NeVA, and LLaVA.
        vision_models=(
            "*llama-3.2-*vision*",
            "*llava*",
            "*vila*",
            "*neva*",
        ),
    ),
    "compatible": ProviderPreset(
        id="compatible",
        label="Custom OpenAI-compatible",
        base_url="",
        default_model="gpt-4o-mini",
        aliases=("custom", "local", "vllm", "ollama"),
        notes="Set AI_BASE_URL yourself (Ollama, vLLM, etc.). "
        "If your local model accepts images, set SCREEN_FORCE_VISION=true "
        "and AI_MODEL to your vision-capable endpoint.",
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


# Curated, concrete vision-capable model id per provider — used in WARN messages
# to nudge users toward a working screen-mode model rather than a text-only default.
_VISION_SUGGESTIONS: dict[str, str] = {
    "openai": "gpt-4o-mini",
    "groq": "meta-llama/llama-4-scout-17b-16e-instruct",
    "gemini": "gemini-2.0-flash",
    "openrouter": "openai/gpt-4o-mini",
    "xai": "grok-2-vision-1212",
    "nvidia": "meta/llama-3.2-90b-vision-instruct",
    "deepseek": "",
    "compatible": "",
    "mock": "",
}


def model_supports_vision(provider_id: str, model: str) -> bool:
    """Best-effort check: does this provider's current model accept image input?

    Conservative on purpose — unknown providers/models return False so the
    pipeline can fall back to OCR-only instead of silently POSTing an image to
    an endpoint that will 400.
    """
    if not provider_id or not model:
        return False
    mid = provider_id.strip().lower()
    if mid == "mock":
        return False
    preset = PROVIDERS.get(mid)
    if preset is None or not preset.vision_models:
        return False
    return any(fnmatchcase(model, pat) for pat in preset.vision_models)


def suggested_vision_model(provider_id: str) -> str:
    """A working vision-capable model id for this provider, or '' if none."""
    return _VISION_SUGGESTIONS.get((provider_id or "").strip().lower(), "")
