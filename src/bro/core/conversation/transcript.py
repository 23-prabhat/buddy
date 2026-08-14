from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Deque


@dataclass(slots=True)
class TranscriptLine:
    speaker: str
    text: str
    ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "microphone"


class RollingTranscript:
    """Time-windowed meeting transcript."""

    def __init__(self, window_seconds: int = 120, max_lines: int = 500) -> None:
        self.window_seconds = window_seconds
        self._lines: Deque[TranscriptLine] = deque(maxlen=max_lines)

    def add(self, speaker: str, text: str, source: str = "microphone") -> TranscriptLine:
        line = TranscriptLine(speaker=speaker, text=text.strip(), source=source)
        if line.text:
            self._lines.append(line)
        self._prune()
        return line

    def _prune(self) -> None:
        if self.window_seconds <= 0:
            return
        now = datetime.now(timezone.utc)
        while self._lines:
            age = (now - self._lines[0].ts).total_seconds()
            if age > self.window_seconds:
                self._lines.popleft()
            else:
                break

    def clear(self) -> None:
        self._lines.clear()

    def lines(self) -> list[TranscriptLine]:
        self._prune()
        return list(self._lines)

    def format_text(self) -> str:
        items = self.lines()
        if not items:
            return ""
        out: list[str] = []
        for ln in items:
            stamp = ln.ts.strftime("%H:%M:%S")
            out.append(f"{stamp} {ln.speaker}:\n\"{ln.text}\"")
        return "\n\n".join(out)

    def __len__(self) -> int:
        return len(self.lines())
