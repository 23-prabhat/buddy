from __future__ import annotations

import io
import struct
import wave

from bro.audio.stt.base import SpeechToTextProvider, TranscriptSegment


def pcm16_to_wav_bytes(pcm: bytes, sample_rate: int = 16000, channels: int = 1) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buf.getvalue()


class OpenAIWhisperSTT(SpeechToTextProvider):
    name = "openai-whisper"

    def __init__(self, api_key: str, model: str = "whisper-1", base_url: str | None = None) -> None:
        if not api_key:
            raise ValueError("AI_API_KEY required for OpenAI Whisper STT")
        from openai import AsyncOpenAI

        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = AsyncOpenAI(**kwargs)
        self._model = model

    async def transcribe(self, pcm: bytes, sample_rate: int = 16000) -> TranscriptSegment:
        wav = pcm16_to_wav_bytes(pcm, sample_rate=sample_rate)
        bio = io.BytesIO(wav)
        bio.name = "audio.wav"
        resp = await self._client.audio.transcriptions.create(
            model=self._model,
            file=bio,
        )
        text = getattr(resp, "text", None) or str(resp)
        return TranscriptSegment(text=text.strip(), confidence=None)
