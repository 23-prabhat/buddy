import pytest

from bro.apps.desktop.terminal.session import TerminalSession
from bro.core.commands import build_registry
from bro.core.configuration.settings import Settings


@pytest.mark.asyncio
async def test_meeting_inject_triggers_answer():
    lines: list[str] = []
    s = Settings()
    # force mock
    object.__setattr__(s, "ai_provider", "mock") if False else None
    session = TerminalSession(
        registry=build_registry(),
        settings=Settings(),
        on_line=lambda t, st: lines.append(t),
    )
    # Ensure mock provider
    from bro.ai.providers.mock import MockAIProvider

    session.provider = MockAIProvider()
    session._screen.ai = session.provider

    await session.inject_meeting_text("Why did you choose PostgreSQL?")
    joined = "\n".join(lines)
    assert "QUESTION" in joined or "PostgreSQL" in joined
    # memory should have assistant reply when question detected
    hist = session.memory.history()
    assert any(m.role == "assistant" for m in hist) or "QUESTION" in joined
