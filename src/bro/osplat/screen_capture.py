from __future__ import annotations

import io
import sys

from bro.osplat.base import PlatformService, Screenshot


class MssScreenCapture(PlatformService):
    """Cross-platform capture via mss (X11/Windows; Wayland may need portal)."""

    def list_monitors(self) -> list[dict]:
        import mss

        with mss.mss() as sct:
            out: list[dict] = []
            for i, mon in enumerate(sct.monitors):
                out.append(
                    {
                        "index": i,
                        "left": mon.get("left"),
                        "top": mon.get("top"),
                        "width": mon.get("width"),
                        "height": mon.get("height"),
                    }
                )
            return out

    def capture_screen(self, monitor: int = 0) -> Screenshot:
        import mss
        from PIL import Image

        with mss.mss() as sct:
            monitors = sct.monitors
            idx = monitor if 0 <= monitor < len(monitors) else 1 if len(monitors) > 1 else 0
            mon = monitors[idx]
            raw = sct.grab(mon)
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            return Screenshot(
                png_bytes=buf.getvalue(),
                width=img.width,
                height=img.height,
                monitor_index=idx,
            )


def get_platform_service() -> PlatformService:
    _ = sys.platform
    return MssScreenCapture()
