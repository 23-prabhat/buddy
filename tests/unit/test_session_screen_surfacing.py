from __future__ import annotations

import io

import pytest

from bro.ai.providers.base import AIProvider
from bro.apps.desktop.terminal.session import TerminalSession
from bro.core.commands import build_registry
from bro.core.configuration.settings import Settings
from bro.osplat.base import PlatformService, Screenshot
from bro.vision.ocr.base import OcrProvider, OcrResult


class _FakeOcr(OcrProvider):
    name = "fake-ocr"

    def extract(self, png_bytes: bytes) -> OcrResult:
        return OcrResult(text="useful enough text from the screen", engine=self.name)


class _FakePlatform(PlatformService):
    def __init__(self) -> None:
        from PIL import Image

        img = Image.new("RGB", (8, 8), (1, 2, 3))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        self.shot = Screenshot(png_bytes=buf.getvalue(), width=8, height=8, monitor_index=0)

    def capture_screen(self, monitor: int = 0) -> Screenshot:
        return self.shot

    def capture_region(self, x: int, y: int, width: int, height: int) -> Screenshot:
        return self.shot

    def list_monitors(self) -> list[dict]:
        return []


class _VisionFakeAI(AIProvider):
    """Vision-capable fake; would raise if the pipeline wrongly POSTed an image."""

    name = "openai"
    model = "gpt-4o-mini"
    supports_vision = True

    async def answer_stream(self, package):  # type: ignore[override]
        yield "(cheap text-only answer from screen OCR)"

    async def analyze_screen(self, image: bytes, prompt: str) -> str:  # noqa: D401
        raise AssertionError("vision should not be called when OCR suffices")


class _TextOnlyFakeAI(AIProvider):
    """Stand-in for a text-only model (e.g. Groq default)."""

    name = "groq"
    model = "llama-3.3-70b-versatile"
    supports_vision = False

    async def answer_stream(self, package):  # type: ignore[override]
        yield "(cheap text-only answer after OCR fallback)"

    async def analyze_screen(self, image: bytes, prompt: str) -> str:  # noqa: D401
        raise AssertionError("vision should not be called for a text-only model")


def _new_session(capture: list) -> TerminalSession:
    return TerminalSession(
        registry=build_registry(),
        settings=Settings(),
        on_line=lambda t, s: capture.append((t, s)),
    )


@pytest.mark.asyncio
async def test_session_screen_analyze_ocr_sufficient_skips_vision_and_no_warn():
    """OCR-sufficient text path: no warn, no vision, AI answers from OCR text."""
    lines: list[tuple[str, str]] = []
    session = _new_session(lines)
    fake_ai = _VisionFakeAI()
    session.provider = fake_ai
    session._screen.ai = fake_ai
    session._screen.ocr = _FakeOcr()
    session._screen.platform = _FakePlatform()
    session._screen.force_vision = False  # OCR-first per spec

    await session.run_screen_analyze(question="why does this traceback segfault here")

    assert not any(t.startswith("[WARN]") for t, _ in lines)
    assert not any(t.startswith("[VISION]") for t, _ in lines)
    assert any("useful enough text from the screen" in t for t, _ in lines)
    # The cheap text-only answer flowed into memory.
    hist = session.memory.history()
    assert any(
        m.role == "assistant" and "OCR" in m.content for m in hist
    ), f"expected assistant answer, got: {[m.content for m in hist]}"


@pytest.mark.asyncio
async def test_session_screen_analyze_warns_when_model_not_vision_capable():
    """Text-only model + vision-asking question -> visible [WARN] line, no crash."""
    lines: list[tuple[str, str]] = []
    session = _new_session(lines)
    fake_ai = _TextOnlyFakeAI()
    session.provider = fake_ai
    session._screen.ai = fake_ai
    session._screen.ocr = _FakeOcr()
    session._screen.platform = _FakePlatform()
    session._screen.force_vision = True  # vision requested -> must surface the gap

    await session.run_screen_analyze(question="what does this icon mean")

    joined = "\n".join(t for t, _ in lines)
    assert any(t.startswith("[WARN]") for t, _ in lines), joined
    assert "does not support" in joined
    # The warning names the offending model + provider for the user.
    assert "llama-3.3-70b-versatile" in joined
    assert "groq" in joined
    # Pipeline did not crash and the AI still produced an OCR-only answer.
    hist = session.memory.history()
    assert any(
        m.role == "assistant" and "OCR" in m.content for m in hist
    ), f"expected assistant answer after OCR-only fallback, got: {[m.content for m in hist]}"


@pytest.mark.asyncio
async def test_session_screen_read_surfaces_capture_errors():
    """A broken platform must surface as [ERROR], never silently swallowed."""
    lines: list[tuple[str, str]] = []
    session = _new_session(lines)
    fake_ai = _VisionFakeAI()
    session.provider = fake_ai
    session._screen.ai = fake_ai
    session._screen.ocr = _FakeOcr()

    class _BoomPlatform(PlatformService):
        def capture_screen(self, monitor: int = 0) -> Screenshot:
            raise RuntimeError("mss: no screens available")

        def capture_region(self, x: int, y: int, w: int, h: int) -> Screenshot:
            raise RuntimeError("mss region: no screens")

        def list_monitors(self) -> list[dict]:
            return []

    session._screen.platform = _BoomPlatform()

    await session.run_screen_read()

    joined = "\n".join(t for t, _ in lines)
    assert any(t.startswith("[ERROR]") for t, _ in lines), joined
    assert "Screen capture failed" in joined
    assert "mss: no screens available" in joined