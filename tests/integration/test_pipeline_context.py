import pytest

from bro.ai.providers.mock import MockAIProvider
from bro.core.configuration.settings import Settings
from bro.core.context.engine import AssistantContext, ContextEngine


@pytest.mark.asyncio
async def test_context_to_llm():
    engine = ContextEngine(Settings())
    pkg = engine.build(
        AssistantContext(
            user_question="Explain the architecture",
            meeting_transcript='10:00 Speaker A:\n"Can you explain this architecture?"',
            current_screen_text="API Gateway -> Service -> DB",
            rag_context="Auth uses JWT.",
            mode="meeting+screen",
        )
    )
    assert "architecture" in pkg.user_content.lower()
    assert "Screen" in pkg.user_content or "screen" in pkg.user_content.lower()
    answer = await MockAIProvider().answer(pkg)
    assert answer
