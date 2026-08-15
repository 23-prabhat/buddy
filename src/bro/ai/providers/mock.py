from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from bro.ai.providers.base import AIProvider
from bro.core.context.engine import ContextPackage


class MockAIProvider(AIProvider):
    """Offline provider for UI/dev without API keys."""

    name = "mock"
    model = "mock"
    supports_vision = False

    async def answer_stream(self, package: ContextPackage) -> AsyncIterator[str]:
        q = package.user_content.strip().splitlines()
        question = next((line for line in q if line and not line.startswith("#")), "your question")
        screen_note = ""
        if "Screen text" in package.user_content or "Screen description" in package.user_content:
            screen_note = " Screen context was included in the prompt."
        text = (
            f"Short answer: I understood — {question[:120]}\n\n"
            f"Details: This is the mock AI provider.{screen_note} "
            "Set AI_PROVIDER=openai (or another OpenAI-compatible endpoint) and "
            "AI_API_KEY in .env for real answers."
        )
        for word in text.split(" "):
            yield word + " "
            await asyncio.sleep(0.02)

    async def analyze_screen(self, image: bytes, prompt: str) -> str:
        size_kb = max(1, len(image) // 1024)
        return (
            f"[mock vision] Received PNG (~{size_kb} KB).\n"
            f"Prompt: {prompt[:200]}\n"
            "No real vision model is configured. OCR text (if any) is still stored "
            "in screen context. Set AI_PROVIDER=openai and a vision-capable AI_MODEL "
            "(e.g. gpt-4o-mini) with AI_API_KEY for real screen understanding."
        )
