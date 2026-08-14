from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator


@dataclass(slots=True)
class AudioChunk:
    pcm: bytes
    sample_rate: int
    channels: int = 1


class AudioSource(ABC):
    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    async def read(self) -> AsyncIterator[AudioChunk]:
        if False:  # pragma: no cover
            yield AudioChunk(b"", 16000)
