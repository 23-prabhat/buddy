from __future__ import annotations

from bro.audio.stt.base import SpeechToTextProvider, TranscriptSegment


class MockSTTProvider(SpeechToTextProvider):
    name = "mock"

    def __init__(self, fixed_text: str | None = None) -> None:
        self.fixed_text = fixed_text

    async def transcribe(self, pcm: bytes, sample_rate: int = 16000) -> TranscriptSegment:
        dur = len(pcm) / 2 / sample_rate if sample_rate else 0
        text = self.fixed_text or f"[mock transcript {dur:.1f}s audio — set STT_PROVIDER=openai]"
        return TranscriptSegment(text=text, confidence=0.5)
