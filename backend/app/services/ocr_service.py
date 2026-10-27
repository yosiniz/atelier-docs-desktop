from __future__ import annotations

import io
import os
import shutil
import sys
import tempfile
from pathlib import Path

import fitz
from PIL import Image, ImageOps, ImageSequence


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


def _recognize(image: Image.Image, language: str, config: str, engine) -> tuple[list[dict], list[float]]:
    prepared = ImageOps.autocontrast(ImageOps.grayscale(image))
    data = engine.image_to_data(prepared, lang=language, config=f"{config} --oem 1 --psm 3".strip(), output_type=engine.Output.DICT)
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
        words.append({"text": text, "left": int(data["left"][index]), "top": int(data["top"][index]), "width": int(data["width"][index]), "height": int(data["height"][index]), "confidence": confidence})
        confidences.append(confidence)
    return words, confidences


def _add_text_layer(page: fitz.Page, words: list[dict], scale_x: float, scale_y: float) -> None:
    font = _ocr_font()
    font_name = "OCRSans" if font else "helv"
    if font:
        page.insert_font(fontname=font_name, fontfile=str(font))
    for word in words:
        x = word["left"] * scale_x
        y = word["top"] * scale_y
        height = max(4.0, word["height"] * scale_y)
        page.insert_text((x, y + height * 0.88), word["text"], fontsize=max(4.0, height * 0.82), fontname=font_name, render_mode=3, overlay=True)


def ocr_pdf(path: Path, output: Path, language: str = "tur+eng", dpi: int = 200, force: bool = False) -> dict:
    engine, tessdata, installed = _configure_engine()
    actual_language, missing = _language(language, installed)
    config = f'--tessdata-dir {tessdata.as_posix()}' if tessdata else ""
    confidences: list[float] = []
    word_count = processed = skipped = 0
    page_results: list[dict] = []
    with fitz.open(path) as source:
        if source.needs_pass:
            raise ValueError("Şifreli PDF için önce kilidi açın")
        result = fitz.open()
        result.insert_pdf(source)
        for page_index, source_page in enumerate(source):
            if not force and len(source_page.get_text("words")) >= 4:
                skipped += 1
                page_results.append({"page": page_index + 1, "status": "skipped", "words": 0, "confidence": 0})
                continue
            pixmap = source_page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), alpha=False)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            words, page_confidences = _recognize(image, actual_language, config, engine)
            _add_text_layer(result[page_index], words, source_page.rect.width / image.width, source_page.rect.height / image.height)
            processed += 1
            word_count += len(words)
            confidences.extend(page_confidences)
            page_results.append({"page": page_index + 1, "status": "processed", "words": len(words), "confidence": round(sum(page_confidences) / len(page_confidences), 1) if page_confidences else 0})
        if processed == 0:
            result.close()
            raise ValueError("Belgenin tüm sayfalarında zaten metin katmanı var")
        result.save(output, garbage=4, deflate=True, clean=True)
        result.close()
    return {"language": actual_language, "requested_language": language, "missing_languages": missing, "word_count": word_count, "average_confidence": round(sum(confidences) / len(confidences), 1) if confidences else 0, "pages_processed": processed, "pages_skipped": skipped, "page_results": page_results}


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
                    image.save(stream, format="JPEG", quality=94, optimize=True)
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
