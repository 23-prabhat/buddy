from bro.vision.ocr.base import OcrResult
from bro.vision.ocr.tesseract import TesseractOcrProvider


def test_ocr_result_useful():
    assert OcrResult(text="hello world code 12345", engine="t").useful
    assert not OcrResult(text="hi", engine="t").useful
    assert not OcrResult(text="enough text here!!", engine="t", error="fail").useful


def test_tesseract_missing_binary_graceful(monkeypatch):
    p = TesseractOcrProvider()
    monkeypatch.setattr(p, "available", lambda: False)
    r = p.extract(b"not-a-png")
    assert r.error
    assert "tesseract" in r.error.lower()
