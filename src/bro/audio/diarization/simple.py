from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SpeakerLabel:
    id: str
    source: str  # "microphone" | "system" | "unknown"


class SimpleDiarizer:
    """
    MVP speaker awareness:
    - audio from the user microphone → User
    - audio tagged as system/meeting → Speaker A/B by crude turn taking
    """

    def __init__(self) -> None:
        self._external_turn = 0
        self._last_external = "Speaker A"

    def label(self, source: str = "microphone") -> str:
        src = (source or "unknown").lower()
        if src in ("microphone", "mic", "user"):
            return "User"
        # external / system / meeting
        self._external_turn += 1
        # alternate A/B every utterance for crude separation
        label = "Speaker A" if self._external_turn % 2 == 1 else "Speaker B"
        self._last_external = label
        return label
