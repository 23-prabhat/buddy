from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class Screenshot:
    png_bytes: bytes
    width: int
    height: int
    monitor_index: int = 0


class PlatformService(ABC):
    @abstractmethod
    def capture_screen(self, monitor: int = 0) -> Screenshot:
        """Capture a monitor. monitor=0 means primary / full virtual screen per impl."""

    @abstractmethod
    def capture_region(self, x: int, y: int, width: int, height: int) -> Screenshot:
        """Capture a rectangular region of the virtual desktop (screen coords)."""

    @abstractmethod
    def list_monitors(self) -> list[dict]:
        """Return monitor metadata for selection."""
