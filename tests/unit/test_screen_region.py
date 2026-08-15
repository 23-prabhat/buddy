from __future__ import annotations

import io

import pytest

from bro.osplat.base import PlatformService, Screenshot
from bro.osplat.screen_capture import crop_screenshot
from bro.vision.ocr.base import OcrProvider, OcrResult
from bro.vision.pipeline import ScreenPipeline


class FakeAI:
    name = "fake"

    async def analyze_screen(self, image: bytes, prompt: str) -> str:
        return "VISION-OK"


class FakePlatform(PlatformService):
    def __init__(self, shot: Screenshot) -> None:
        self.shot = shot
        self.region_calls: list[tuple[int, int, int, int]] = []

    def capture_screen(self, monitor: int = 0) -> Screenshot:
        return self.shot

    def capture_region(self, x: int, y: int, width: int, height: int) -> Screenshot:
        self.region_calls.append((x, y, width, height))
        return crop_screenshot(self.shot, x, y, width, height)

    def list_monitors(self) -> list[dict]:
        return [{"index": 0, "left": 0, "top": 0, "width": 100, "height": 60}]


class FakeOcr(OcrProvider):
    name = "fake-ocr"

    def extract(self, png_bytes: bytes) -> OcrResult:
        return OcrResult(text="hello screen region world", engine=self.name)


def _screenshot(size: int = 100) -> Screenshot:
    from PIL import Image

    img = Image.new("RGB", (size, size), (10, 20, 30))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Screenshot(png_bytes=buf.getvalue(), width=size, height=size, monitor_index=0)


@pytest.mark.asyncio
async def test_pipeline_captures_whole_monitor():
    shot = _screenshot()
    pipe = ScreenPipeline(FakePlatform(shot), FakeOcr(), FakeAI())
    res = await pipe.understand(monitor=0)
    assert res.screenshot.width == 100
    assert "monitor=0" in res.source_summary


@pytest.mark.asyncio
async def test_pipeline_captures_live_region():
    shot = _screenshot(100)
    plat = FakePlatform(shot)
    pipe = ScreenPipeline(plat, FakeOcr(), FakeAI())
    res = await pipe.understand(region=(10, 10, 40, 40))
    assert plat.region_calls == [(10, 10, 40, 40)]
    assert res.screenshot.width == 40
    assert "region=10,10+40x40" in res.source_summary


@pytest.mark.asyncio
async def test_pipeline_crops_pre_captured_screenshot():
    shot = _screenshot(100)
    plat = FakePlatform(shot)
    pipe = ScreenPipeline(plat, FakeOcr(), FakeAI())
    # Pass the full screenshot + region => crop, no live capture.
    res = await pipe.understand(region=(5, 5, 20, 25), screenshot=shot)
    assert plat.region_calls == []  # did NOT re-capture from screen
    assert res.screenshot.width == 20
    assert res.screenshot.height == 25
    assert "region=5,5+20x25" in res.source_summary


def test_crop_screenshot_clamps_and_returns_png():
    shot = _screenshot(50)
    crop = crop_screenshot(shot, 0, 0, 60, 60)  # clamp beyond edges
    assert crop.width == 50
    assert crop.height == 50
    # output is valid PNG
    from PIL import Image

    img = Image.open(io.BytesIO(crop.png_bytes))
    assert img.size == (50, 50)