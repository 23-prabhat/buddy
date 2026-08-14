from __future__ import annotations

from dataclasses import dataclass

from bro.ai.providers.base import AIProvider
from bro.osplat.base import PlatformService, Screenshot
from bro.vision.ocr.base import OcrProvider, OcrResult


@dataclass
class ScreenUnderstanding:
    screenshot: Screenshot
    ocr: OcrResult
    description: str
    used_vision: bool
    source_summary: str


class ScreenPipeline:
    """Capture → OCR → optional multimodal vision."""

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
    ) -> ScreenUnderstanding:
        shot = self.capture(monitor=monitor)
        ocr = self.ocr.extract(shot.png_bytes)
        description = ""
        used_vision = False

        want_vision = self.force_vision if use_vision is None else use_vision
        if want_vision is False and ocr.useful and not question:
            description = "OCR text available; vision model skipped."
        else:
            # Use vision when OCR weak, or user asked a question, or forced
            need = want_vision or (not ocr.useful) or bool(question)
            if need:
                prompt = question or (
                    "Describe what is on this screen. Focus on code, errors, UI text, "
                    "diagrams, and any questions visible. Be concise and structured."
                )
                if ocr.text:
                    prompt += f"\n\nOCR extract (may be noisy):\n{ocr.text[:3000]}"
                try:
                    description = await self.ai.analyze_screen(shot.png_bytes, prompt)
                    used_vision = True
                except NotImplementedError:
                    description = (
                        "Vision analyze not supported by current AI provider. "
                        "Using OCR only. Set AI_PROVIDER=openai with a vision-capable model."
                    )
                except Exception as exc:  # noqa: BLE001
                    description = f"Vision model failed: {exc}"
            else:
                description = "OCR sufficient for text extraction."

        summary_bits = [
            f"{shot.width}x{shot.height}",
            f"monitor={shot.monitor_index}",
            f"ocr={ocr.engine}" + (" ok" if ocr.useful else " weak/empty"),
            f"vision={'yes' if used_vision else 'no'}",
        ]
        return ScreenUnderstanding(
            screenshot=shot,
            ocr=ocr,
            description=description.strip(),
            used_vision=used_vision,
            source_summary=", ".join(summary_bits),
        )
