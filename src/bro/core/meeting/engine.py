from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from bro.ai.reasoning.question_detect import QuestionDetector
from bro.audio.capture.base import AudioSource
from bro.audio.diarization.simple import SimpleDiarizer
from bro.audio.stt.base import SpeechToTextProvider
from bro.audio.vad.energy import EnergyVAD
from bro.core.conversation.transcript import RollingTranscript


OnLine = Callable[[str, str], None]  # text, style
OnQuestion = Callable[[str, str], Awaitable[None]]  # question, speaker


@dataclass
class MeetingStatus:
    running: bool
    lines: int
    last_text: str
    stt: str


class MeetingEngine:
    """
    Mic → VAD → STT → rolling transcript → question detect → callback.
    """

    def __init__(
        self,
        audio: AudioSource,
        stt: SpeechToTextProvider,
        transcript: RollingTranscript,
        on_line: OnLine | None = None,
        on_question: OnQuestion | None = None,
        auto_answer: bool = True,
        audio_source_label: str = "microphone",
    ) -> None:
        self.audio = audio
        self.stt = stt
        self.transcript = transcript
        self.on_line = on_line or (lambda _t, _s: None)
        self.on_question = on_question
        self.auto_answer = auto_answer
        self.audio_source_label = audio_source_label
        self.vad = EnergyVAD()
        self.diarizer = SimpleDiarizer()
        self.detector = QuestionDetector()
        self._task: asyncio.Task | None = None
        self._running = False
        self._last_text = ""

    @property
    def running(self) -> bool:
        return self._running

    def status(self) -> MeetingStatus:
        return MeetingStatus(
            running=self._running,
            lines=len(self.transcript),
            last_text=self._last_text,
            stt=self.stt.name,
        )

    async def start(self) -> None:
        if self._running:
            return
        await self.audio.start()
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._running = False
        try:
            await self.audio.stop()
        except Exception:  # noqa: BLE001
            pass
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        leftover = self.vad.flush()
        if leftover:
            await self._handle_utterance(leftover)

    async def _loop(self) -> None:
        try:
            async for chunk in self.audio.read():
                if not self._running:
                    break
                _speaking, utterance = self.vad.process(chunk.pcm)
                if utterance:
                    await self._handle_utterance(utterance, sample_rate=chunk.sample_rate)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            self.on_line(f"[ERROR] Meeting audio loop: {exc}", "error")
            self._running = False

    async def _handle_utterance(self, pcm: bytes, sample_rate: int = 16000) -> None:
        try:
            seg = await self.stt.transcribe(pcm, sample_rate=sample_rate)
        except Exception as exc:  # noqa: BLE001
            self.on_line(f"[ERROR] STT failed: {exc}", "error")
            return
        text = (seg.text or "").strip()
        if not text:
            return
        speaker = self.diarizer.label(self.audio_source_label)
        if seg.speaker:
            speaker = seg.speaker
        self._last_text = text
        self.transcript.add(speaker=speaker, text=text, source=self.audio_source_label)
        self.on_line(f'{speaker}: "{text}"', "info")

        det = self.detector.detect(text, speaker=speaker)
        if det.is_question and det.directed_at_user:
            self.on_line(
                f"[QUESTION] Detected (conf={det.confidence:.2f}) · {det.reason}",
                "system",
            )
            if self.auto_answer and self.on_question:
                await self.on_question(det.normalized, speaker)

    async def inject_text(self, text: str, speaker: str = "Speaker A") -> None:
        """Test/dev helper: push text as if transcribed."""
        self._last_text = text
        self.transcript.add(speaker=speaker, text=text, source="inject")
        self.on_line(f'{speaker}: "{text}"', "info")
        det = self.detector.detect(text, speaker=speaker)
        if det.is_question and det.directed_at_user:
            self.on_line(
                f"[QUESTION] Detected (conf={det.confidence:.2f}) · {det.reason}",
                "system",
            )
            if self.auto_answer and self.on_question:
                await self.on_question(det.normalized, speaker)
