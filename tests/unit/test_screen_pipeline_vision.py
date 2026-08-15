from __future__ import annotations

import io

import pytest

from bro.osplat.base import PlatformService, Screenshot
from bro.osplat.screen_capture import crop_screenshot
from bro.vision.ocr.base import OcrProvider, OcrResult
from bro.vision.pipeline import ScreenPipeline


class VisionFakeAI:
    """AI provider that advertises itself as vision-capable."""

    name = "openai"
    model = "gpt-4o-mini"
    supports_vision = True

    def __init__(self) -> None:
        self.calls: list[tuple[bytes, str]] = []

    async def analyze_screen(self, image: bytes, prompt: str) -> str:
        self.calls.append((image, prompt))
        return "VISION-OK"


class TextOnlyFakeAI:
    """AI provider with no image support (mimics a text-only model)."""

    name = "groq"
    model = "llama-3.3-70b-versatile"
    supports_vision = False

    def __init__(self) -> None:
        self.calls: list[tuple[bytes, str]] = []

    async def analyze_screen(self, image: bytes, prompt: str) -> str:
        self.calls.append((image, prompt))
        return "should-not-be-called"


class NoAttrFakeAI:
    """Old-style AI provider object without the supports_vision attr.

    Some test fakes (and any out-of-tree AIProvider subclass written before this
    change) may not set supports_vision. The pipeline must NOT crash and must
    treat them as text-only.
    """

    name = "weird"

    async def analyze_screen(self, image: bytes, prompt: str) -> str:
        raise AssertionError("should not be called")


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


class UsefulOcr(OcrProvider):
    name = "useful-ocr"

    def extract(self, png_bytes: bytes) -> OcrResult:
        return OcrResult(
            text="Traceback: ValueError at line 42 in pipeline.understand",
            engine=self.name,
        )


class EmptyOcr(OcrProvider):
    name = "empty-ocr"

    def extract(self, png_bytes: bytes) -> OcrResult:
        return OcrResult(text="", engine=self.name)


def _screenshot(size: int = 100) -> Screenshot:
    from PIL import Image

    img = Image.new("RGB", (size, size), (10, 20, 30))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Screenshot(png_bytes=buf.getvalue(), width=size, height=size, monitor_index=0)


@pytest.mark.asyncio
async def test_ocr_useful_text_question_skips_vision_call():
    """OCR has real text and the question is text-only -> no vision POST."""
    ai = VisionFakeAI()
    pipe = ScreenPipeline(FakePlatform(_screenshot()), UsefulOcr(), ai)
    res = await pipe.understand(question="why does this traceback segfault here")
    assert res.used_vision is False
    assert res.description == ""
    assert ai.calls == []  # vision endpoint never contacted
    assert res.warning is None


@pytest.mark.asyncio
async def test_ocr_useful_and_no_question_skips_vision():
    """A bare `screen read` with useful OCR should not call vision."""
    ai = VisionFakeAI()
    pipe = ScreenPipeline(FakePlatform(_screenshot()), UsefulOcr(), ai)
    res = await pipe.understand(question=None)
    assert res.used_vision is False
    assert ai.calls == []


@pytest.mark.asyncio
async def test_ocr_useful_but_question_about_icon_calls_vision():
    """A vision-keyword question forces the multimodal call even with good OCR."""
    ai = VisionFakeAI()
    pipe = ScreenPipeline(FakePlatform(_screenshot()), UsefulOcr(), ai)
    res = await pipe.understand(question="what does this icon mean")
    assert res.used_vision is True
    assert res.description == "VISION-OK"
    assert len(ai.calls) == 1
    assert res.warning is None


@pytest.mark.asyncio
async def test_ocr_useful_vision_keyword_chart_calls_vision():
    ai = VisionFakeAI()
    pipe = ScreenPipeline(FakePlatform(_screenshot()), UsefulOcr(), ai)
    res = await pipe.understand(question="describe this chart for me")
    assert res.used_vision is True


@pytest.mark.asyncio
async def test_ocr_empty_calls_vision_when_supported():
    """No usable OCR text -> the only way to describe the screen is vision."""
    ai = VisionFakeAI()
    pipe = ScreenPipeline(FakePlatform(_screenshot()), EmptyOcr(), ai)
    res = await pipe.understand(question="explain what is on this screen")
    assert res.used_vision is True
    assert res.description == "VISION-OK"
    assert ai.calls


@pytest.mark.asyncio
async def test_text_only_model_warns_and_does_not_crash():
    """Model advertises no image support -> warn line, fall back to OCR, no throw."""
    ai = TextOnlyFakeAI()
    pipe = ScreenPipeline(FakePlatform(_screenshot()), UsefulOcr(), ai)
    res = await pipe.understand(question="what does this icon mean")
    assert res.used_vision is False
    assert ai.calls == []  # definitely did not POST an image
    assert res.warning is not None
    assert res.warning.startswith("[WARN]")
    assert "does not support" in res.warning
    # The warning names the offending model and provider so the user can fix it.
    assert "llama-3.3-70b-versatile" in res.warning
    assert "groq" in res.warning


@pytest.mark.asyncio
async def test_text_only_model_warning_suggests_vision_model():
    """The warn must point the user at a working vision-capable model."""
    from bro.ai.providers.catalog import suggested_vision_model

    ai = TextOnlyFakeAI()
    pipe = ScreenPipeline(FakePlatform(_screenshot()), UsefulOcr(), ai)
    res = await pipe.understand(question="describe this logo")
    sug = suggested_vision_model(ai.name)
    assert sug, "groq should have a known vision-capable suggestion"
    assert sug in (res.warning or "")


@pytest.mark.asyncio
async def test_no_attr_ai_does_not_crash_and_warns():
    """An AI object missing supports_vision entirely is treated as text-only."""
    ai = NoAttrFakeAI()
    pipe = ScreenPipeline(FakePlatform(_screenshot()), EmptyOcr(), ai)
    res = await pipe.understand(question="what does this icon mean")
    assert res.used_vision is False
    assert res.warning is not None
    assert res.warning.startswith("[WARN]")


@pytest.mark.asyncio
async def test_force_vision_with_supported_model_calls_vision():
    ai = VisionFakeAI()
    pipe = ScreenPipeline(FakePlatform(_screenshot()), UsefulOcr(), ai, force_vision=True)
    res = await pipe.understand(question=None)
    assert res.used_vision is True
    assert ai.calls


@pytest.mark.asyncio
async def test_force_vision_with_text_only_model_warns():
    ai = TextOnlyFakeAI()
    pipe = ScreenPipeline(FakePlatform(_screenshot()), UsefulOcr(), ai, force_vision=True)
    res = await pipe.understand(question=None)
    assert res.used_vision is False
    assert ai.calls == []
    assert res.warning is not None


@pytest.mark.asyncio
async def test_explicit_use_vision_true_calls_vision_when_supported():
    ai = VisionFakeAI()
    pipe = ScreenPipeline(FakePlatform(_screenshot()), UsefulOcr(), ai, force_vision=False)
    res = await pipe.understand(question="explain this code", use_vision=True)
    assert res.used_vision is True


@pytest.mark.asyncio
async def test_explicit_use_vision_false_overrides_force():
    """Per-call use_vision=False must beat force_vision=True."""
    ai = VisionFakeAI()
    pipe = ScreenPipeline(FakePlatform(_screenshot()), UsefulOcr(), ai, force_vision=True)
    res = await pipe.understand(question="why this error", use_vision=False)
    assert res.used_vision is False
    assert ai.calls == []


@pytest.mark.asyncio
async def test_vision_exception_surfaces_as_warning():
    """If the backend raises, we surface a WARN instead of losing the request."""

    class BoomAI(VisionFakeAI):
        async def analyze_screen(self, image: bytes, prompt: str) -> str:
            raise RuntimeError("upstream 400 bad request")

    ai = BoomAI()
    pipe = ScreenPipeline(FakePlatform(_screenshot()), EmptyOcr(), ai)
    res = await pipe.understand(question="describe this picture")
    assert res.used_vision is False
    assert res.warning is not None
    assert "Vision model failed" in res.warning
    assert "upstream 400 bad request" in res.warning


def test_question_needs_vision_keyword_heuristic_positive():
    assert ScreenPipeline._question_needs_vision("what does this icon mean") is True
    assert ScreenPipeline._question_needs_vision("Describe this chart.") is True
    assert ScreenPipeline._question_needs_vision("WHAT COLOR IS THE LOGO?") is True


def test_question_needs_vision_keyword_heuristic_negative():
    assert ScreenPipeline._question_needs_vision("why is this segfault happening") is False
    assert ScreenPipeline._question_needs_vision("explain this stack trace") is False
    assert ScreenPipeline._question_needs_vision(None) is False
    assert ScreenPipeline._question_needs_vision("") is False