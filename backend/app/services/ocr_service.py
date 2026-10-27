from __future__ import annotations

import io
import json
import math
import os
import shutil
import sys
import tempfile
from pathlib import Path

import fitz
from PIL import Image, ImageOps, ImageSequence

from .ocr_preprocessing import prepare_scan, original_rect


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _ascii_cache_root() -> Path:
    candidates = [
        Path(os.environ.get("ProgramData", "C:/ProgramData")) / "AtelierDocs/OCR",
        Path(os.environ.get("PUBLIC", "C:/Users/Public")) / "Documents/AtelierDocs/OCR",
    ]
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            if str(candidate).isascii():
                return candidate
        except OSError:
            continue
    raise RuntimeError("OCR için ASCII karakterli geçici klasör oluşturulamadı")


def find_tesseract() -> Path | None:
    candidates = [
        os.environ.get("ATELIER_TESSERACT_CMD"),
        shutil.which("tesseract"),
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Tesseract-OCR/tesseract.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Tesseract-OCR/tesseract.exe",
        Path("/opt/homebrew/bin/tesseract"),
        Path("/usr/local/bin/tesseract"),
        _project_root() / "ocr-runtime/windows/tesseract.exe",
    ]
    if getattr(sys, "_MEIPASS", None):
        candidates.append(Path(sys._MEIPASS) / "ocr/windows/tesseract.exe")
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    return None


def _tessdata_dir(executable: Path) -> Path | None:
    candidates = [
        os.environ.get("TESSDATA_PREFIX"),
        _project_root() / "assets/tessdata",
        executable.parent / "tessdata",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_dir() and any(Path(candidate).glob("*.traineddata")):
            selected = Path(candidate)
            if os.name == "nt" and not str(selected).isascii():
                # Tesseract's Windows build still uses an ANSI path internally.
                # Keep its language cache in a stable ASCII-only system folder.
                cache = _ascii_cache_root() / "tessdata"
                try:
                    cache.mkdir(parents=True, exist_ok=True)
                    for language_file in selected.glob("*.traineddata"):
                        target = cache / language_file.name
                        if not target.exists() or target.stat().st_size != language_file.stat().st_size:
                            shutil.copy2(language_file, target)
                    selected = cache
                except OSError:
                    pass
            return selected
    return None


def _configure_engine() -> tuple[object, Path | None, set[str]]:
    executable = find_tesseract()
    if not executable:
        raise RuntimeError("Yerel OCR motoru bulunamadı. Uygulamayın OCR destekli kurulumunu yeniden yükleyin.")
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = str(executable)
    if os.name == "nt":
        # pytesseract writes every page to a temporary image before invoking
        # Tesseract. Some Windows builds cannot report errors for a path that
        # contains Turkish characters without producing non-UTF-8 stderr.
        temp_root = _ascii_cache_root() / "tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        tempfile.tempdir = str(temp_root)
    tessdata = _tessdata_dir(executable)
    config = f'--tessdata-dir {tessdata.as_posix()}' if tessdata else ""
    # Listing the local traineddata files avoids a pytesseract decoding bug on
    # Windows user profiles containing Turkish characters.
    languages = {item.stem for item in tessdata.glob("*.traineddata")} if tessdata else set()
    if not languages:
        try:
            languages = set(pytesseract.get_languages(config=config))
        except (pytesseract.TesseractError, UnicodeError) as exc:
            raise RuntimeError(f"OCR dil dosyaları okunamadı: {exc}") from exc
    return pytesseract, tessdata, languages


def ocr_engine_status() -> dict:
    try:
        _engine, _data, languages = _configure_engine()
        return {"available": True, "languages": sorted(languages), "turkish": "tur" in languages}
    except RuntimeError:
        return {"available": False, "languages": [], "turkish": False}


def _language(requested: str, installed: set[str]) -> tuple[str, list[str]]:
    requested_languages = requested.split("+")
    available = [item for item in requested_languages if item in installed]
    missing = [item for item in requested_languages if item not in installed]
    if not available:
        raise RuntimeError(f"İstenen OCR dil paketleri bulunamadı: {requested}")
    return "+".join(available), missing


def _ocr_font() -> Path | None:
    candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    ]
    return next((item for item in candidates if item.is_file()), None)


def _recognize(image: Image.Image, language: str, config: str, engine, *, layout="auto", enhance=True, deskew=True) -> tuple[list[dict], list[float]]:
    prepared, inverse, angle = prepare_scan(image, enhance=enhance, deskew=deskew, table=layout == "table")
    psm = {"auto": 3, "document": 6, "table": 11, "sparse": 11}[layout]

    def recognize(psm_value):
        try:
            return engine.image_to_data(prepared, lang=language,
                config=f"{config} --oem 1 --psm {psm_value} -c preserve_interword_spaces=1".strip(),
                output_type=engine.Output.DICT, timeout=90)
        except RuntimeError as exc:
            raise RuntimeError("OCR sayfası 90 saniyede tamamlanamadı. Daha düşük çözünürlükle yeniden deneyin.") from exc

    def score(data):
        return sum(len(str(text).strip()) * max(0, float(conf) - 35)
                   for text, conf in zip(data.get("text", []), data.get("conf", [])))

    data = recognize(psm)
    # A sparse fallback helps receipts, forms and pages where automatic page
    # segmentation finds no useful text. Keep one pass, never duplicate words.
    if layout == "auto":
        usable = [float(conf) for text, conf in zip(data.get("text", []), data.get("conf", [])) if str(text).strip() and float(conf) >= 0]
        if not usable or sum(usable) / len(usable) < 75:
            fallback = recognize(11)
            if score(fallback) > score(data):
                data = fallback
    words: list[dict] = []
    confidences: list[float] = []
    for index, raw_text in enumerate(data.get("text", [])):
        text = str(raw_text).strip()
        try:
            confidence = float(data["conf"][index])
        except (ValueError, TypeError, KeyError):
            confidence = -1
        if not text or confidence < 0:
            continue
        left, top, right, bottom = original_rect(int(data["left"][index]), int(data["top"][index]), int(data["width"][index]), int(data["height"][index]), inverse)
        left, top = max(0.0, left), max(0.0, top)
        right, bottom = min(float(image.width), right), min(float(image.height), bottom)
        if right <= left or bottom <= top:
            continue
        words.append({"text": text, "left": left, "top": top, "width": right-left, "height": bottom-top, "confidence": confidence, "deskew_angle": angle})
        confidences.append(confidence)
    return words, confidences


def _add_text_layer(page: fitz.Page, words: list[dict], scale_x: float, scale_y: float) -> None:
    # Normalize the page's rotation into its content before placing OCR boxes.
    # This retains its rendered appearance and gives the editor one coordinate
    # system for the preview, selection, redaction and new text.
    if page.rotation:
        page.remove_rotation()
    font = _ocr_font()
    font_name = "OCRSans" if font else "helv"
    if font:
        page.insert_font(fontname=font_name, fontfile=str(font))
    metrics = fitz.Font(fontfile=str(font)) if font else fitz.Font("helv")
    review_words = []
    for word in words:
        x = word["left"] * scale_x
        y = word["top"] * scale_y
        height = max(1.0, word["height"] * scale_y)
        width = max(1.0, word["width"] * scale_x)
        # Fit both axes to the recognized glyph box. The old fixed point size
        # produced hitboxes much narrower/wider than the scanned word.
        size = height / (metrics.ascender - metrics.descender)
        baseline = fitz.Point(x, y + metrics.ascender * size)
        natural_width = max(0.01, metrics.text_length(word["text"], fontsize=size))
        rect = fitz.Rect(x, y, x + width, y + height)
        transform = fitz.Matrix(width / natural_width, 1)
        page.insert_text(baseline, word["text"], fontsize=size, fontname=font_name, render_mode=3,
                         morph=(baseline, transform), overlay=True)
        review_words.append({"text": word["text"], "rect": list(rect), "confidence": word["confidence"]})
    page.parent.xref_set_key(page.xref, "AtelierOCR", fitz.get_pdf_str(json.dumps(review_words, ensure_ascii=False)))


def ocr_pdf(path: Path, output: Path, language: str = "tur+eng", dpi: int = 300, force: bool = False,
            *, layout: str = "auto", enhance: bool = True, deskew: bool = True,
            pages: list[int] | None = None, progress=None, cancel_event=None) -> dict:
    engine, tessdata, installed = _configure_engine()
    actual_language, missing = _language(language, installed)
    config = f'--tessdata-dir {tessdata.as_posix()}' if tessdata else ""
    confidences: list[float] = []
    word_count = processed = skipped = 0
    page_results: list[dict] = []
    with fitz.open(path) as source:
        if source.needs_pass:
            raise ValueError("Şifreli PDF için önce kilidi açın")
        if pages is not None and any(index < 0 or index >= len(source) for index in pages):
            raise ValueError("OCR sayfa seçimi belge sınırları dışında")
        result = fitz.open(path)
        for page_index, source_page in enumerate(source):
            if cancel_event and cancel_event.is_set():
                result.close()
                raise RuntimeError("OCR iptal edildi")
            if progress:
                progress(round(5 + 85 * page_index / len(source)))
            traces = source_page.get_texttrace()
            visible_text = any(trace.get("type") != 3 and trace.get("chars") for trace in traces)
            invisible_text = any(trace.get("type") == 3 and trace.get("chars") for trace in traces)
            visible_rects = [fitz.Rect(trace["bbox"]) for trace in traces if trace.get("type") != 3 and trace.get("chars")]
            scan_background = any(
                fitz.Rect(info["bbox"]).get_area() >= source_page.rect.get_area() * .5
                for info in source_page.get_image_info()
            )
            hybrid_scan = scan_background and len(source_page.get_text("words")) < 20
            if (pages is not None and page_index not in pages) or (visible_text and not hybrid_scan) or (invisible_text and not force):
                skipped += 1
                page_results.append({"page": page_index + 1, "status": "skipped", "words": 0, "confidence": 0})
                continue
            # Bound raster memory even for architectural/oversized PDF pages.
            factor = min(dpi / 72, math.sqrt(24_000_000 / max(1, source_page.rect.width * source_page.rect.height)))
            pixmap = source_page.get_pixmap(matrix=fitz.Matrix(factor, factor), alpha=False)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            words, page_confidences = _recognize(image, actual_language, config, engine, layout=layout, enhance=enhance, deskew=deskew)
            if visible_rects:
                kept = []
                for word in words:
                    rect = fitz.Rect(word["left"], word["top"], word["left"] + word["width"], word["top"] + word["height"])
                    rect = fitz.Rect(rect.x0 * source_page.rect.width / image.width, rect.y0 * source_page.rect.height / image.height,
                                     rect.x1 * source_page.rect.width / image.width, rect.y1 * source_page.rect.height / image.height) * source_page.derotation_matrix
                    if not any((rect & existing).get_area() > rect.get_area() * .4 for existing in visible_rects):
                        kept.append(word)
                words = kept
                page_confidences = [word["confidence"] for word in words]
            if invisible_text:
                target_page = result[page_index]
                for trace in traces:
                    if trace.get("type") == 3 and trace.get("chars"):
                        target_page.add_redact_annot(trace["bbox"], fill=False)
                target_page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_NONE)
            _add_text_layer(result[page_index], words, source_page.rect.width / image.width, source_page.rect.height / image.height)
            processed += 1
            word_count += len(words)
            confidences.extend(page_confidences)
            page_results.append({"page": page_index + 1, "status": "processed", "words": len(words), "low_confidence_words": sum(c < 65 for c in page_confidences), "deskew_angle": words[0]["deskew_angle"] if words else 0, "confidence": round(sum(page_confidences) / len(page_confidences), 1) if page_confidences else 0})
        if processed == 0:
            result.close()
            raise ValueError("Seçilen sayfalarda metin katmanı var. Eski OCR'ı iyileştirmek için 'Eski OCR katmanını yeniden tanı' seçeneğini açın.")
        if word_count == 0:
            result.close()
            raise ValueError("Okunabilir metin bulunamadı. Tablo/Form modunu veya daha net bir taramayı deneyin; belge değiştirilmedi.")
        result.save(output, garbage=4, deflate=True, clean=True)
        result.close()
    return {"language": actual_language, "requested_language": language, "missing_languages": missing, "word_count": word_count, "low_confidence_words": sum(c < 65 for c in confidences), "average_confidence": round(sum(confidences) / len(confidences), 1) if confidences else 0, "pages_processed": processed, "pages_skipped": skipped, "page_results": page_results}


def ocr_images_to_pdf(paths: list[Path], output: Path, language: str = "tur+eng", dpi: int = 200) -> dict:
    engine, tessdata, installed = _configure_engine()
    actual_language, missing = _language(language, installed)
    config = f'--tessdata-dir {tessdata.as_posix()}' if tessdata else ""
    result = fitz.open()
    confidences: list[float] = []
    word_count = pages = 0
    try:
        for path in paths:
            with Image.open(path) as opened:
                for frame in ImageSequence.Iterator(opened):
                    image = ImageOps.exif_transpose(frame.copy()).convert("RGB")
                    words, page_confidences = _recognize(image, actual_language, config, engine)
                    page_width, page_height = image.width * 72 / dpi, image.height * 72 / dpi
                    page = result.new_page(width=page_width, height=page_height)
                    stream = io.BytesIO()
                    image.save(stream, format="PNG")
                    page.insert_image(page.rect, stream=stream.getvalue())
                    _add_text_layer(page, words, page_width / image.width, page_height / image.height)
                    word_count += len(words)
                    confidences.extend(page_confidences)
                    pages += 1
        if pages == 0:
            raise ValueError("OCR için okunabilir görsel bulunamadı")
        result.save(output, garbage=4, deflate=True, clean=True)
    finally:
        result.close()
    return {"language": actual_language, "requested_language": language, "missing_languages": missing, "word_count": word_count, "average_confidence": round(sum(confidences) / len(confidences), 1) if confidences else 0, "pages_processed": pages, "pages_skipped": 0}
