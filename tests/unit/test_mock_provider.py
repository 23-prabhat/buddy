import pytest

from bro.ai.providers.mock import MockAIProvider
from bro.core.context.engine import ContextPackage


@pytest.mark.asyncio
async def test_mock_streams():
    p = MockAIProvider()
    pkg = ContextPackage(
        system_prompt="sys",
        user_content="## User question\nHello",
        messages=[],
    )
    chunks = []
    async for c in p.answer_stream(pkg):
        chunks.append(c)
    text = "".join(chunks)
    assert "mock" in text.lower() or "Hello" in text
