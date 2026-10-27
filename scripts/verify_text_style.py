"""Visual acceptance sample for automatic scanned-text style matching."""
from pathlib import Path
import fitz
from backend.app.models import TextEditRequest
from backend.app.services.ocr_service import _add_text_layer, _ocr_font
from backend.app.services.pdf_service import edit_text, text_blocks


output = Path(__file__).resolve().parents[1] / "output/pdf"
output.mkdir(parents=True, exist_ok=True)
font = _ocr_font()
assert font
source = output / "style-scan-source.pdf"
with fitz.open() as original:
    page = original.new_page(width=500, height=250)
    page.draw_rect(page.rect, fill=(.94, .93, .9), overlay=False)
    for y, color in [(85, (.42, .42, .42)), (160, (.15, .25, .5))]:
        page.insert_text((60, y), "RAPOR", fontsize=28, color=color, fontname="Original", fontfile=str(font))
    rects = [word[:4] for word in page.get_text("words")]
    pix = page.get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False)
    with fitz.open() as scanned:
        scan = scanned.new_page(width=500, height=250)
        scan.insert_image(scan.rect, stream=pix.tobytes("png"))
        _add_text_layer(scan, [{"text": "RAPOR", "left": r[0], "top": r[1], "width": r[2]-r[0], "height": r[3]-r[1], "confidence": 95} for r in rects], 1, 1)
        scanned.save(source)
current = source
for index in range(2):
    block = next(block for block in text_blocks(current, 0) if block["text"] == "RAPOR")
    target = output / f"style-match-{index+1}.pdf"
    edit_text(current, target, TextEditRequest(page=0, rect=block["bbox"], text="BELGE", original_text="RAPOR", preserve_style=True))
    current = target
for path, name in [(source, "style-before.png"), (current, "style-after.png")]:
    with fitz.open(path) as document:
        document[0].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).save(output / name)
print("Visual style sample created")
