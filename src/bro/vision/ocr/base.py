from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class OcrResult:
    text: str
    engine: str
    confidence: float | None = None
    error: str | None = None

    @property
    def useful(self) -> bool:
        if self.error:
            return False
        cleaned = "".join(ch for ch in self.text if ch.isalnum())
        return len(cleaned) >= 12


class OcrProvider(ABC):
    name: str = "base"

    @abstractmethod
    def extract(self, png_bytes: bytes) -> OcrResult: ...
