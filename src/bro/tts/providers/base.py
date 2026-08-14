from __future__ import annotations

from abc import ABC, abstractmethod


class TTSProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def speak(self, text: str) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...
