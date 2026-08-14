from bro.core.configuration.settings import Settings


def test_public_dict_redacts_key(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "secret-value")
    monkeypatch.setenv("AI_PROVIDER", "mock")
    s = Settings()
    pub = s.public_dict()
    assert pub["ai_api_key"] == "set"
    assert "secret-value" not in str(pub)


def test_defaults():
    s = Settings()
    assert s.meeting_context_seconds == 120
