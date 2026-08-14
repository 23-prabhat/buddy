from __future__ import annotations

import struct
from dataclasses import dataclass


@dataclass
class VadConfig:
    threshold: float = 500.0  # RMS on int16 scale
    hangover_ms: int = 400
    min_speech_ms: int = 250


class EnergyVAD:
    """Simple energy-based VAD — no native deps."""

    def __init__(self, sample_rate: int = 16000, config: VadConfig | None = None) -> None:
        self.sample_rate = sample_rate
        self.config = config or VadConfig()
        self._speech = False
        self._silence_ms = 0.0
        self._speech_ms = 0.0
        self._buffer = bytearray()

    @staticmethod
    def rms_int16(pcm: bytes) -> float:
        if len(pcm) < 2:
            return 0.0
        n = len(pcm) // 2
        samples = struct.unpack(f"<{n}h", pcm[: n * 2])
        if not samples:
            return 0.0
        acc = sum(s * s for s in samples) / len(samples)
        return acc**0.5

    def process(self, pcm: bytes) -> tuple[bool, bytes | None]:
        """
        Feed PCM chunk.
        Returns (is_speech_now, completed_utterance_or_None).
        """
        ms = (len(pcm) // 2) / self.sample_rate * 1000.0
        energy = self.rms_int16(pcm)
        speaking = energy >= self.config.threshold

        if speaking:
            self._speech = True
            self._silence_ms = 0.0
            self._speech_ms += ms
            self._buffer.extend(pcm)
            return True, None

        if self._speech:
            self._silence_ms += ms
            self._buffer.extend(pcm)
            if self._silence_ms >= self.config.hangover_ms:
                utt = bytes(self._buffer)
                long_enough = self._speech_ms >= self.config.min_speech_ms
                self._reset()
                return False, utt if long_enough else None
            return True, None

        return False, None

    def flush(self) -> bytes | None:
        if self._speech and self._speech_ms >= self.config.min_speech_ms:
            utt = bytes(self._buffer)
            self._reset()
            return utt
        self._reset()
        return None

    def _reset(self) -> None:
        self._speech = False
        self._silence_ms = 0.0
        self._speech_ms = 0.0
        self._buffer.clear()
