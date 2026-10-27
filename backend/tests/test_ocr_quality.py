import io
import time
from types import SimpleNamespace

import fitz
import pytest
from PIL import Image

from backend.app.services import ocr_service
from backend.app.services.ocr_preprocessing import prepare_scan, original_rect
from backend.app.services.pdf_service import text_blocks, edit_text, inspect_pdf
from backend.app.models import TextEditRequest


def scan_pdf(tmp_path, image, rotation=0):
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    path = tmp_path / "scan.pdf"
    with fitz.open() as document:
        page = document.new_page(width=image.width * .36, height=image.height * .36)
        page.insert_image(page.rect, stream=stream.getvalue())
        page.set_rotation(rotation)
        document.set_metadata({"title": "Original scan"})
        document.save(path)
    return path


def fake_engine(monkeypatch):
    monkeypatch.setattr(ocr_service, "_configure_engine", lambda: (object(), None, {"tur", "eng"}))
    def recognize(image, *_args, **_kwargs):
        return [{"text": "TEST", "left": 100, "top": 100, "width": 250, "height": 50,
                 "confidence": 52, "deskew_angle": 0}], [52]
    monkeypatch.setattr(ocr_service, "_recognize", recognize)


def test_layer_alignment_confidence_and_rerun_do_not_duplicate(tmp_path, monkeypatch):
    fake_engine(monkeypatch)
    source = scan_pdf(tmp_path, Image.new("RGB", (1000, 1400), "white"))
    output = tmp_path / "ocr.pdf"
    audit = ocr_service.ocr_pdf(source, output, dpi=200)
    assert audit["low_confidence_words"] == 1
    blocks = text_blocks(output, 0)
    assert len(blocks) == 1
    assert blocks[0]["confidence"] == 52
    assert blocks[0]["is_ocr"]
    assert blocks[0]["bbox"] == pytest.approx([36, 36, 126, 54], abs=.2)
    with fitz.open(source) as before, fitz.open(output) as after:
        assert before[0].get_pixmap().samples == after[0].get_pixmap().samples
        assert after.metadata["title"] == "Original scan"
    rerun = tmp_path / "rerun.pdf"
    ocr_service.ocr_pdf(output, rerun, dpi=200, force=True)
    with fitz.open(rerun) as document:
        assert document[0].get_text().count("TEST") == 1


def test_ocr_edit_removes_scan_pixels_not_only_invisible_text(tmp_path):
    image = Image.new("RGB", (1000, 1400), "white")
    from PIL import ImageDraw
    ImageDraw.Draw(image).rectangle((100, 100, 350, 150), fill="black")
    source = scan_pdf(tmp_path, image)
    layered = tmp_path / "layered.pdf"
    with fitz.open(source) as document:
        ocr_service._add_text_layer(document[0], [{"text": "TEST", "left": 100, "top": 100,
                                                 "width": 250, "height": 50, "confidence": 90}], .36, .36)
        document.save(layered)
    block = text_blocks(layered, 0)[0]
    output = tmp_path / "deleted.pdf"
    edit_text(layered, output, TextEditRequest(page=0, rect=block["bbox"], original_text="TEST", text=""))
    assert b"TEST" not in output.read_bytes()
    with fitz.open(output) as document:
        assert "TEST" not in document[0].get_text()
        pix = document[0].get_pixmap(clip=fitz.Rect(40, 40, 120, 50), colorspace=fitz.csGRAY)
        assert min(pix.samples) > 240


@pytest.mark.parametrize("operation", ["replace", "redact"])
def test_removed_ocr_word_does_not_survive_in_review_metadata(tmp_path, operation):
    from backend.app.services.pdf_service import replace_text, redact_areas
    from backend.app.models import SearchReplaceRequest
    source = scan_pdf(tmp_path, Image.new("RGB", (1000, 1400), "white"))
    layered = tmp_path / "layer.pdf"
    with fitz.open(source) as document:
        ocr_service._add_text_layer(document[0], [{"text": "SECRET", "left": 100, "top": 100,
                                                 "width": 250, "height": 50, "confidence": 90}], .36, .36)
        document.save(layered)
    output = tmp_path / "removed.pdf"
    if operation == "replace":
        replace_text(layered, output, SearchReplaceRequest(query="SECRET", replacement=""))
    else:
        redact_areas(layered, output, 0, [(30, 30, 130, 60)])
    assert b"SECRET" not in output.read_bytes()
    with fitz.open(output) as document:
        assert "SECRET" not in document[0].get_text()
        assert "SECRET" not in document.xref_get_key(document[0].xref, "AtelierOCR")[1]


@pytest.mark.parametrize("rotation", [90, 180, 270])
def test_rotated_layer_stays_in_displayed_word_box(tmp_path, monkeypatch, rotation):
    fake_engine(monkeypatch)
    source = scan_pdf(tmp_path, Image.new("RGB", (1000, 1400), "white"), rotation=rotation)
    output = tmp_path / "rotated.pdf"
    ocr_service.ocr_pdf(source, output, dpi=200)
    with fitz.open(output) as document:
        words = document[0].get_text("words")
        assert len(words) == 1
        rect = fitz.Rect(words[0][:4]) * document[0].rotation_matrix
        assert list(rect) == pytest.approx([36, 36, 126, 54], abs=1)


def test_hybrid_page_number_does_not_prevent_scan_ocr(tmp_path, monkeypatch):
    fake_engine(monkeypatch)
    source = scan_pdf(tmp_path, Image.new("RGB", (1000, 1400), "white"))
    hybrid = tmp_path / "hybrid.pdf"
    with fitz.open(source) as document:
        document[0].insert_text((100, 480), "Page 1")
        document.save(hybrid)
    assert inspect_pdf(hybrid)["scanned_likely"]
    output = tmp_path / "hybrid-ocr.pdf"
    ocr_service.ocr_pdf(hybrid, output, dpi=200)
    with fitz.open(output) as document:
        assert "TEST" in document[0].get_text()
        assert document[0].get_text().count("Page 1") == 1


def test_empty_ocr_does_not_create_success_output(tmp_path, monkeypatch):
    fake_engine(monkeypatch)
    monkeypatch.setattr(ocr_service, "_recognize", lambda *_args, **_kwargs: ([], []))
    source = scan_pdf(tmp_path, Image.new("RGB", (1000, 1400), "white"))
    output = tmp_path / "empty-ocr.pdf"
    with pytest.raises(ValueError, match="Okunabilir metin"):
        ocr_service.ocr_pdf(source, output)
    assert not output.exists()


def test_preprocessing_inverse_maps_skew_to_original():
    from PIL import ImageDraw
    import numpy as np
    image = Image.new("RGB", (1000, 800), "white")
    draw = ImageDraw.Draw(image)
    for y in range(100, 700, 80):
        draw.line((60, y, 930, y + 32), fill="black", width=3)
    prepared, inverse, angle = prepare_scan(image, enhance=True, deskew=True, table=False)
    assert prepared.size == image.size
    assert 1 < abs(angle) < 4
    rect = original_rect(100, 100, 200, 40, inverse)
    assert all(np.isfinite(rect))
    assert rect[2] > rect[0] and rect[3] > rect[1]


def test_cancel_and_invalid_page_leave_original_untouched(tmp_path, monkeypatch):
    fake_engine(monkeypatch)
    source = scan_pdf(tmp_path, Image.new("RGB", (1000, 1400), "white"))
    original = source.read_bytes()
    with pytest.raises(RuntimeError, match="iptal"):
        ocr_service.ocr_pdf(source, tmp_path / "cancelled.pdf", cancel_event=SimpleNamespace(is_set=lambda: True))
    with pytest.raises(ValueError, match="sınırları"):
        ocr_service.ocr_pdf(source, tmp_path / "invalid.pdf", pages=[7])
    assert original == source.read_bytes()


def test_queued_ocr_reports_progress_and_persistent_result(client, scanned_document_png, tmp_path):
    with Image.open(scanned_document_png) as image:
        source = scan_pdf(tmp_path, image)
    with source.open("rb") as handle:
        uploaded = client.post("/api/files", files={"file": (source.name, handle, "application/pdf")}).json()["data"]
    queued = client.post(f"/api/jobs/pdf/{uploaded['id']}/ocr", json={"layout": "table", "dpi": 200})
    assert queued.status_code == 200
    job = queued.json()["data"]
    for _ in range(200):
        job = client.get(f"/api/jobs/{job['id']}").json()["data"]
        if job["status"] in {"completed", "failed"}:
            break
        time.sleep(.05)
    assert job["status"] == "completed", job
    assert job["progress"] == 100
    assert job["result"]["audit"]["word_count"] > 0
    assert job["result"]["pdf"]["scanned_likely"] is False
