"""Local OCR acceptance check: Turkish, faint forms, skew, persistence and visual fidelity."""
import json
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont

from backend.app.services.ocr_service import ocr_pdf
from backend.app.services.pdf_service import text_blocks


root = Path(__file__).resolve().parents[1]
output = root / "output/pdf"
output.mkdir(parents=True, exist_ok=True)
font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 40)
heading = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 52)
image = Image.new("RGB", (1654, 2339), (240, 238, 230))
draw = ImageDraw.Draw(image)
draw.text((140, 140), "TARANMIŞ BELGE / FATURA", fill=(70, 70, 70), font=heading)
rows = ["Müşteri", "Yusuf Subaşı", "Fatura numarası", "12345", "Ödeme tarihi", "27.10.2026", "Toplam tutar", "3.142,15 TL"]
for y in range(350, 951, 150):
    draw.line((120, y, 1500, y), fill=(130, 130, 130), width=2)
for x in (120, 800, 1500):
    draw.line((x, 350, x, 950), fill=(130, 130, 130), width=2)
for index, label in enumerate(rows):
    draw.text((145 if index % 2 == 0 else 825, 395 + (index // 2) * 150), label, fill=(100, 100, 100), font=font)
draw.text((140, 1100), "Türkçe karakterler: ç ğ ı İ ö ş ü", fill=(100, 100, 100), font=font)
image = image.rotate(1.7, resample=Image.Resampling.BICUBIC, fillcolor=(240, 238, 230))
image_path = output / "ocr-quality-source.png"
image.save(image_path)
source = output / "ocr-quality-source.pdf"
with fitz.open() as document:
    page = document.new_page(width=595.44, height=842.04)
    page.insert_image(page.rect, filename=str(image_path))
    document.save(source)
target = output / "ocr-quality-improved.pdf"
audit = ocr_pdf(source, target, dpi=300, layout="table")
with fitz.open(source) as before, fitz.open(target) as after:
    unchanged = before[0].get_pixmap().samples == after[0].get_pixmap().samples
    text = after[0].get_text()
    assert "12345" in text and "3.142,15" in text, text
    assert unchanged, "OCR modified the original scan appearance"
    preview = after[0].get_pixmap(matrix=fitz.Matrix(1.25, 1.25), alpha=False)
    preview.save(output / "ocr-quality-preview.png")
blocks = text_blocks(target, 0)
assert all(block["confidence"] is not None for block in blocks), blocks
print(json.dumps({"audit": audit, "visual_unchanged": unchanged, "text": text,
                  "editable_words": len(blocks)}, ensure_ascii=True, indent=2))
