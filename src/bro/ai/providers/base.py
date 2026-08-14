from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from bro.core.context.engine import ContextPackage


class AIProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def answer_stream(self, package: ContextPackage) -> AsyncIterator[str]:
        """Yield answer tokens/chunks."""
        if False:  # pragma: no cover
            yield ""

    async def answer(self, package: ContextPackage) -> str:
        chunks: list[str] = []
        async for chunk in self.answer_stream(package):
            chunks.append(chunk)
        return "".join(chunks)

    async def analyze_screen(self, image: bytes, prompt: str) -> str:
        raise NotImplementedError("Screen analysis not implemented for this provider")

    def info(self) -> dict[str, Any]:
        return {"name": self.name}
