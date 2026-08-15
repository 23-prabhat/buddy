from __future__ import annotations

from bro.ai.providers.catalog import (
    PROVIDERS,
    model_supports_vision,
    suggested_vision_model,
)


def test_openai_gpt4o_patterns_match():
    assert model_supports_vision("openai", "gpt-4o-mini") is True
    assert model_supports_vision("openai", "gpt-4o") is True
    assert model_supports_vision("openai", "gpt-4o-2024-08-06") is True


def test_openai_text_only_model_returns_false():
    # gpt-3.5-turbo does not accept images
    assert model_supports_vision("openai", "gpt-3.5-turbo") is False


def test_groq_default_text_model_not_vision():
    # The free-tier default must NOT silently claim image support.
    assert model_supports_vision("groq", "llama-3.3-70b-versatile") is False


def test_groq_vision_models_match():
    assert model_supports_vision("groq", "meta-llama/llama-4-scout-17b-16e-instruct") is True
    assert model_supports_vision("groq", "meta-llama/llama-3.2-90b-vision-preview") is True


def test_gemini_default_model_treated_as_vision():
    assert model_supports_vision("gemini", "gemini-2.0-flash") is True
    assert model_supports_vision("gemini", "gemini-1.5-pro") is True


def test_openrouter_namespaced_model_matches():
    # OpenRouter routes namespaced model ids like "openai/gpt-4o-mini".
    assert model_supports_vision("openrouter", "openai/gpt-4o-mini") is True
    assert model_supports_vision("openrouter", "anthropic/claude-3.5-sonnet") is True


def test_deepseek_has_no_known_vision_models():
    assert model_supports_vision("deepseek", "deepseek-chat") is False


def test_mock_provider_is_never_vision():
    assert model_supports_vision("mock", "mock") is False


def test_compatible_provider_is_conservative():
    # We cannot know the custom endpoint's model -> safe default is False.
    assert model_supports_vision("compatible", "my-llava-thing") is False


def test_unknown_provider_is_conservative():
    assert model_supports_vision("totally-fictional", "gpt-4o") is False
    assert model_supports_vision("", "gpt-4o") is False
    assert model_supports_vision("openai", "") is False


def test_suggested_vision_model_present_for_major_providers():
    for pid in ("openai", "groq", "gemini", "openrouter", "xai", "nvidia"):
        assert suggested_vision_model(pid), f"{pid} should have a vision suggestion"


def test_suggested_vision_model_absent_for_text_only_or_unknown():
    assert suggested_vision_model("deepseek") == ""
    assert suggested_vision_model("compatible") == ""
    assert suggested_vision_model("mock") == ""
    assert suggested_vision_model("nonexistent") == ""


def test_every_preset_has_vision_models_field_defaulted():
    # The new field exists on every preset (empty tuple by default), so providers
    # without known vision models degrade cleanly instead of erroring.
    for _pid, preset in PROVIDERS.items():
        assert isinstance(preset.vision_models, tuple)
        for pat in preset.vision_models:
            assert isinstance(pat, str) and pat