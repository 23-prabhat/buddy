from __future__ import annotations

import io
import shutil

from bro.vision.ocr.base import OcrProvider, OcrResult


class TesseractOcrProvider(OcrProvider):
    name = "tesseract"

    def __init__(self, lang: str = "eng") -> None:
        self.lang = lang

    def available(self) -> bool:
        return shutil.which("tesseract") is not None

    def extract(self, png_bytes: bytes) -> OcrResult:
        if not self.available():
            return OcrResult(
                text="",
                engine=self.name,
                error="tesseract binary not found. Install system package `tesseract` / `tesseract-ocr`.",
            )
        try:
            import pytesseract
            from PIL import Image
        except ImportError as exc:
            return OcrResult(text="", engine=self.name, error=f"OCR deps missing: {exc}")

        try:
            img = Image.open(io.BytesIO(png_bytes))
            text = pytesseract.image_to_string(img, lang=self.lang) or ""
            return OcrResult(text=text.strip(), engine=self.name)
        except Exception as exc:  # noqa: BLE001
            return OcrResult(text="", engine=self.name, error=str(exc))
