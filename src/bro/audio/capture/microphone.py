from __future__ import annotations

import asyncio
import queue
import threading
from collections.abc import AsyncIterator

from bro.audio.capture.base import AudioChunk, AudioSource


class MicrophoneAudioSource(AudioSource):
    """Capture mic via sounddevice; falls back with clear error if unavailable."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        block_ms: int = 30,
        device: int | str | None = None,
    ) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.block_ms = block_ms
        self.device = device
        self._q: queue.Queue[bytes | None] = queue.Queue(maxsize=64)
        self._stream = None
        self._running = False
        self._thread: threading.Thread | None = None

    async def start(self) -> None:
        try:
            import sounddevice as sd
            import numpy as np
        except ImportError as exc:
            raise RuntimeError(
                "sounddevice/numpy not installed. "
                "uv pip install numpy sounddevice --python .venv/bin/python"
            ) from exc

        frames = max(1, int(self.sample_rate * self.block_ms / 1000))
        self._running = True

        def callback(indata, _frames, _time, status):  # noqa: ANN001
            if not self._running:
                return
            if status:
                pass
            mono = indata.copy()
            if mono.ndim > 1:
                mono = mono.mean(axis=1)
            pcm = (mono * 32767.0).astype("int16").tobytes()
            try:
                self._q.put_nowait(pcm)
            except queue.Full:
                try:
                    self._q.get_nowait()
                except queue.Empty:
                    pass
                try:
                    self._q.put_nowait(pcm)
                except queue.Full:
                    pass

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            blocksize=frames,
            device=self.device,
            callback=callback,
        )
        self._stream.start()

    async def stop(self) -> None:
        self._running = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:  # noqa: BLE001
                pass
            self._stream = None
        try:
            self._q.put_nowait(None)
        except queue.Full:
            pass

    async def read(self) -> AsyncIterator[AudioChunk]:
        while self._running:
            try:
                item = await asyncio.get_event_loop().run_in_executor(None, self._q.get, True, 0.25)
            except Exception:
                await asyncio.sleep(0.01)
                continue
            if item is None:
                break
            yield AudioChunk(pcm=item, sample_rate=self.sample_rate, channels=self.channels)
