from bro.ai.providers.catalog import resolve_provider_id
from bro.ai.providers.factory import create_ai_provider, describe_ai_config
from bro.core.configuration.settings import Settings


def test_resolve_aliases():
    assert resolve_provider_id("grok") == "xai"
    assert resolve_provider_id("nemotron") == "nvidia"
    assert resolve_provider_id("google") == "gemini"
    assert resolve_provider_id("groq") == "groq"


def test_free_mode_uses_free_key(monkeypatch):
    monkeypatch.setenv("AI_KEY_MODE", "free")
    monkeypatch.setenv("FREE_AI_API_KEY", "gsk_test_free_key_123456")
    monkeypatch.setenv("FREE_AI_PROVIDER", "groq")
    monkeypatch.setenv("FREE_AI_MODEL", "llama-3.3-70b-versatile")
    monkeypatch.setenv("AI_API_KEY", "")
    s = Settings()
    info = describe_ai_config(s)
    assert info["key_mode"] == "free"
    assert info["provider"] == "groq"
    assert info["api_key"] == "set"
    p = create_ai_provider(s)
    assert p.name == "groq"


def test_own_mode_requires_key(monkeypatch):
    monkeypatch.setenv("AI_KEY_MODE", "own")
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("AI_API_KEY", "")
    monkeypatch.setenv("FREE_AI_API_KEY", "gsk_should_not_use")
    s = Settings()
    try:
        create_ai_provider(s)
        assert False, "expected error"
    except ValueError as e:
        assert "key" in str(e).lower()


def test_own_mode_with_key(monkeypatch):
    monkeypatch.setenv("AI_KEY_MODE", "own")
    monkeypatch.setenv("AI_PROVIDER", "deepseek")
    monkeypatch.setenv("AI_API_KEY", "sk-deepseek-test-key")
    monkeypatch.setenv("AI_MODEL", "deepseek-chat")
    s = Settings()
    info = describe_ai_config(s)
    assert info["provider"] == "deepseek"
    assert info["model"] == "deepseek-chat"
    p = create_ai_provider(s)
    assert p.name == "deepseek"
