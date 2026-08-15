from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from bro.core.context.engine import ContextPackage


class AIProvider(ABC):
    name: str = "base"
    # Model id currently configured for this provider, used by callers (e.g. the
    # screen pipeline) to decide whether image input is permitted.
    model: str = ""
    # Whether ``analyze_screen`` can actually POST an image to the backend. Set
    # by concrete providers from the catalog allowlist so the pipeline can warn
    # the user and skip the image call instead of failing silently upstream.
    supports_vision: bool = False

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
        return {"name": self.name, "model": self.model, "supports_vision": self.supports_vision}
