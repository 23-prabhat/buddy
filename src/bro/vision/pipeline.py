from __future__ import annotations

from dataclasses import dataclass

from bro.ai.providers.base import AIProvider
from bro.osplat.base import PlatformService, Screenshot
from bro.osplat.screen_capture import crop_screenshot
from bro.vision.ocr.base import OcrProvider, OcrResult


@dataclass
class ScreenUnderstanding:
    screenshot: Screenshot
    ocr: OcrResult
    description: str
    used_vision: bool
    source_summary: str
    warning: str | None = None


# Keywords that strongly suggest a question needs to "see" the screen, not just
# read the OCR text. Kept lowercase on purpose; matching is substring-based after
# lowercasing the question so we don't need to make a second AI call to decide.
_VISION_KEYWORDS = (
    "icon",
    "icons",
    "image",
    "images",
    "diagram",
    "diagrams",
    "color",
    "color of",
    "colour",
    "colours",
    "logo",
    "logos",
    "picture",
    "pictures",
    "chart",
    "charts",
    "graph",
    "graphs",
    "plot",
    "plots",
    "looks",
    "look",
    "appearance",
    "design",
    "wireframe",
    "mockup",
    "render",
    "renders",
    "rendering",
    "drawing",
    "drawings",
    "paint",
    "painting",
    "photo",
    "photos",
    "photograph",
    "screenshot",
    "screenshots",
    "visual",
    "user interface",
    "ui element",
    "shape",
    "shape of",
    "texture",
)


class ScreenPipeline:
    """Capture -> OCR -> optional multimodal vision.

    Supports three capture modes:
      * whole monitor         (monitor=...)
      * live screen region    (region=(x,y,w,h) in screen coords)
      * pre-captured image    (screenshot=...), optionally cropped to region

    The vision model is only invoked when OCR alone is insufficient to answer
    the user's question (weak/empty OCR or a question that needs visual
    understanding such as "what does this icon mean"). Otherwise the screen text
    is forwarded to the cheap text-only AI path.
    """

    def __init__(
        self,
        platform: PlatformService,
        ocr: OcrProvider,
        ai: AIProvider,
        force_vision: bool = False,
    ) -> None:
        self.platform = platform
        self.ocr = ocr
        self.ai = ai
        self.force_vision = force_vision

    def capture(self, monitor: int = 0) -> Screenshot:
        return self.platform.capture_screen(monitor=monitor)

    async def understand(
        self,
        monitor: int = 0,
        question: str | None = None,
        use_vision: bool | None = None,
        region: tuple[int, int, int, int] | None = None,
        screenshot: Screenshot | None = None,
    ) -> ScreenUnderstanding:
        # Decide the source screenshot.
        if screenshot is not None:
            shot = (
                crop_screenshot(screenshot, *region)
                if region is not None
                else screenshot
            )
        elif region is not None:
            x, y, w, h = region
            shot = self.platform.capture_region(x, y, w, h)
        else:
            shot = self.capture(monitor=monitor)

        ocr = self.ocr.extract(shot.png_bytes)
        description = ""
        used_vision = False
        warning: str | None = None

        want_vision = self._decide_vision(use_vision, self.force_vision, ocr, question)

        if want_vision:
            description, used_vision, warning = await self._call_vision(shot, ocr, question)

        src = (
            f"region={region[0]},{region[1]}+{region[2]}x{region[3]}"
            if region is not None
            else f"monitor={shot.monitor_index}"
        )
        summary_bits = [
            f"{shot.width}x{shot.height}",
            src,
            f"ocr={ocr.engine}" + (" ok" if ocr.useful else " weak/empty"),
            f"vision={'yes' if used_vision else 'no'}",
        ]
        return ScreenUnderstanding(
            screenshot=shot,
            ocr=ocr,
            description=description.strip(),
            used_vision=used_vision,
            source_summary=", ".join(summary_bits),
            warning=warning,
        )

    @staticmethod
    def _question_needs_vision(question: str | None) -> bool:
        """Cheap keyword heuristic — would OCR text alone answer this question?

        We deliberately DO NOT make a second AI call here. Substring keyword
        matching is enough for Phase 1 to tell image-heavy questions ("what does
        this icon mean", "describe this chart" — needs pixels) from text-heavy
        questions ("why this segfault", "explain this code" — OCR suffices).
        """
        if not question:
            return False
        q = question.lower()
        return any(kw in q for kw in _VISION_KEYWORDS)

    def _decide_vision(
        self,
        use_vision: bool | None,
        force_vision: bool,
        ocr: OcrResult,
        question: str | None,
    ) -> bool:
        """Should we attempt the multimodal vision call?

        Ladder (first match wins):

          * explicit override via ``use_vision``  -> caller knows best
          * ``force_vision`` (config / region-select)  -> user wants pixels
          * OCR is not useful / noisy / errored  -> no text to lean on
          * OCR is useful, but the question needs to "see"  -> vision keyword hit
          * otherwise  -> OCR text alone answers it; skip vision
        """
        if use_vision is not None:
            return bool(use_vision)
        if force_vision:
            return True
        if not ocr.useful:
            return True
        return self._question_needs_vision(question)

    async def _call_vision(
        self,
        shot: Screenshot,
        ocr: OcrResult,
        question: str | None,
    ) -> tuple[str, bool, str | None]:
        """Run the vision model, or fall back to OCR-only with a visible WARN.

        Returns ``(description, used_vision, warning)``.
        """
        if not _provider_supports_vision(self.ai):
            return (
                "",
                False,
                _vision_unsupported_warning(self.ai),
            )

        prompt = question or (
            "Describe what is on this screen. Focus on code, errors, UI text, "
            "diagrams, and any questions visible. Be concise and structured."
        )
        if ocr.text:
            prompt += f"\n\nOCR extract (may be noisy):\n{ocr.text[:3000]}"
        try:
            description = await self.ai.analyze_screen(shot.png_bytes, prompt)
            return description, True, None
        except NotImplementedError:
            return (
                "",
                False,
                (
                    "[WARN] Current AI provider does not implement vision analysis. "
                    "Using OCR only. Set AI_PROVIDER / AI_MODEL to a vision-capable "
                    "OpenAI-compatible endpoint (e.g. openai with gpt-4o-mini)."
                ),
            )
        except Exception as exc:  # noqa: BLE001
            # Don't swallow it silently — bubble a visible line up to the session
            # but still keep OCR text as the working context.
            return (
                "",
                False,
                f"[WARN] Vision model failed: {exc}",
            )


def _provider_supports_vision(ai: AIProvider) -> bool:
    """Resolution order: ``supports_vision`` flag on the provider, else False.

    Some test fakes don't subclass ``AIProvider``; rely on ``getattr`` so the
    pipeline can still drive them.
    """
    return bool(getattr(ai, "supports_vision", False))


def _vision_unsupported_warning(ai: AIProvider) -> str:
    """Build a single-line WARN message telling the user how to fix this.

    Uses the live provider/model id so the message is actionable for the
    currently configured backend instead of generic advice.
    """
    from bro.ai.providers.catalog import suggested_vision_model

    provider = getattr(ai, "name", "unknown") or "unknown"
    model = getattr(ai, "model", "") or "(current)"
    suggestion = suggested_vision_model(provider)
    msg = (
        f"[WARN] AI model '{model}' on provider '{provider}' does not support "
        f"image input. Falling back to OCR-only for this screen request."
    )
    if suggestion:
        msg += (
            f" To enable screen-mode vision, set AI_MODEL={suggestion}"
            " in .env (or run: provider " + provider + " " + suggestion + ")."
        )
    else:
        msg += (
            " This provider has no known vision-capable model; switch to a "
            "vision-capable provider (e.g. openai, gemini) in .env, or set "
            "SCREEN_FORCE_VISION=true only if your custom endpoint accepts images."
        )
    return msg