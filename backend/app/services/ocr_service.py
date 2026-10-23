from __future__ import annotations

import os
import shutil
from pathlib import Path

import fitz
from PIL import Image


def ocr_pdf(path: Path, output: Path, language: str = "tur+eng", dpi: int = 200) -> dict:
    executable = os.environ.get("ATELIER_TESSERACT_CMD") or shutil.which("tesseract")
    if not executable:
        raise RuntimeError("Tesseract OCR motoru bulunamadı. Türkçe OCR için Tesseract ve tur dil paketi kurulmalıdır.")
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = executable
    installed = set(pytesseract.get_languages(config=""))
    requested = language.split("+")
    available = [item for item in requested if item in installed]
    if not available:
        raise RuntimeError(f"İstenen OCR dil paketleri bulunamadı: {language}")
    actual_language = "+".join(available)
    scale = 72 / dpi
    confidences: list[float] = []
    word_count = 0
    with fitz.open(path) as source:
        result = fitz.open()
        result.insert_pdf(source)
        for page_index, source_page in enumerate(source):
            pixmap = source_page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), alpha=False)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            data = pytesseract.image_to_data(image, lang=actual_language, output_type=pytesseract.Output.DICT)
            page = result[page_index]
            for index, raw_text in enumerate(data.get("text", [])):
                text = str(raw_text).strip()
                try:
                    confidence = float(data["conf"][index])
                except (ValueError, TypeError, KeyError):
                    confidence = -1
                if not text or confidence < 0:
                    continue
                x, y = data["left"][index] * scale, data["top"][index] * scale
                height = max(4, data["height"][index] * scale)
                page.insert_text((x, y + height), text, fontsize=max(4, height * .82),
                                 fontname="helv", color=(0, 0, 0), render_mode=3, overlay=True)
                confidences.append(confidence)
                word_count += 1
        result.save(output, garbage=4, deflate=True, clean=True)
        result.close()
    return {
        "language": actual_language,
        "requested_language": language,
        "word_count": word_count,
        "average_confidence": round(sum(confidences) / len(confidences), 1) if confidences else 0,
    }
