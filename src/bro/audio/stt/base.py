from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class TranscriptSegment:
    text: str
    confidence: float | None = None
    start_ms: float | None = None
    end_ms: float | None = None
    speaker: str | None = None


class SpeechToTextProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def transcribe(self, pcm: bytes, sample_rate: int = 16000) -> TranscriptSegment: ...
