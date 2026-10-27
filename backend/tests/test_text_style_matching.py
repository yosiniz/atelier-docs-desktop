import fitz
import pytest

from backend.app.models import TextEditRequest
from backend.app.services.ocr_service import _add_text_layer, _ocr_font
from backend.app.services.pdf_service import edit_text, text_blocks
from backend.app.services.text_style_service import source_text_style


def test_digital_replacement_keeps_exact_size_color_and_baseline(tmp_path):
    source = tmp_path / "digital.pdf"
    with fitz.open() as document:
        page = document.new_page()
        page.insert_text((70, 110), "SOURCE", fontsize=17.5, color=(.2, .3, .4), fontname="hebo")
        document.save(source)
    block = text_blocks(source, 0)[0]
    output = tmp_path / "edited.pdf"
    edit_text(source, output, TextEditRequest(page=0, rect=block["bbox"], original_text=block["text"],
                                             text="REPLACED", preserve_style=True))
    replaced = text_blocks(output, 0)[0]
    assert replaced["font_size"] == pytest.approx(17.5, abs=.01)
    assert replaced["color"] == block["color"]
    assert replaced["baseline"] == pytest.approx(block["baseline"], abs=.02)
    assert replaced["bold"]


@pytest.mark.parametrize("color", [(0.45, 0.45, 0.45), (.15, .25, .5)])
def test_scan_matching_samples_real_ink_and_real_size(tmp_path, color):
    font = _ocr_font()
    if not font:
        pytest.skip("No local Unicode font")
    source = tmp_path / "scan.pdf"
    with fitz.open() as digital:
        page = digital.new_page(width=500, height=250)
        page.insert_text((70, 110), "SAMPLE", fontsize=24, color=color, fontname="Original", fontfile=str(font))
        rect = page.get_text("words")[0][:4]
        pix = page.get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False)
        with fitz.open() as scanned:
            target = scanned.new_page(width=500, height=250)
            target.insert_image(target.rect, stream=pix.tobytes("png"))
            _add_text_layer(target, [{"text": "SAMPLE", "left": rect[0], "top": rect[1],
                "width": rect[2]-rect[0], "height": rect[3]-rect[1], "confidence": 95}], 1, 1)
            scanned.save(source)
    with fitz.open(source) as document:
        matched = source_text_style(document[0], fitz.Rect(rect), "SAMPLE")
    assert matched["estimated"]
    assert matched["font_size"] == pytest.approx(24, abs=1)
    actual_color = [int(matched["color"][i:i+2], 16) for i in (1, 3, 5)]
    assert actual_color == pytest.approx([round(value*255) for value in color], abs=3)
    assert matched["baseline"] == pytest.approx(110, abs=1)
    output = tmp_path / "matched.pdf"
    edit_text(source, output, TextEditRequest(page=0, rect=rect, text="NEW", original_text="SAMPLE", preserve_style=True))
    replacement = next(block for block in text_blocks(output, 0) if "NEW" in block["text"])
    assert replacement["font_size"] == pytest.approx(24, abs=1)
    assert replacement["color"] == matched["color"]
    assert b"SAMPLE" not in output.read_bytes()


def test_manual_style_overrides_are_still_respected(tmp_path):
    source = tmp_path / "manual.pdf"
    with fitz.open() as document:
        page = document.new_page()
        page.insert_text((70, 110), "SOURCE", fontsize=12)
        document.save(source)
    block = text_blocks(source, 0)[0]
    output = tmp_path / "manual-edit.pdf"
    edit_text(source, output, TextEditRequest(page=0, rect=block["bbox"], text="MANUAL", preserve_style=False,
                                             style={"font_size": 20, "color": "#123456"}))
    result = text_blocks(output, 0)[0]
    assert result["font_size"] == pytest.approx(20)
    assert result["color"] == "#123456"
