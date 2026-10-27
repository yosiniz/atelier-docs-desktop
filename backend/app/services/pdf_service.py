from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Iterable

import fitz
from pypdf import PdfReader, PdfWriter
from PIL import Image


def _unicode_font(bold: bool = False, italic: bool = False, family: str | None = None) -> Path | None:
    sans_variants = {
        (False, False): ["arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"],
        (True, False): ["arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"],
        (False, True): ["ariali.ttf", "segoeuii.ttf", "DejaVuSans-Oblique.ttf"],
        (True, True): ["arialbi.ttf", "seguisbi.ttf", "DejaVuSans-BoldOblique.ttf"],
    }
    family_key = (family or "").casefold()
    if "times" in family_key or "serif" in family_key:
        windows = {(False, False): ["times.ttf"], (True, False): ["timesbd.ttf"], (False, True): ["timesi.ttf"], (True, True): ["timesbi.ttf"]}
    elif "cour" in family_key or "mono" in family_key:
        windows = {(False, False): ["cour.ttf"], (True, False): ["courbd.ttf"], (False, True): ["couri.ttf"], (True, True): ["courbi.ttf"]}
    elif "calibri" in family_key:
        windows = {(False, False): ["calibri.ttf"], (True, False): ["calibrib.ttf"], (False, True): ["calibrii.ttf"], (True, True): ["calibriz.ttf"]}
    else:
        windows = sans_variants
    candidates = [Path("C:/Windows/Fonts") / name for name in windows[(bold, italic)]]
    candidates.extend(Path("/usr/share/fonts/truetype/dejavu") / name for name in sans_variants[(bold, italic)])
    mac_font_names = {
        (False, False): ["Arial.ttf", "Helvetica.ttc"],
        (True, False): ["Arial Bold.ttf", "HelveticaNeue.ttc"],
        (False, True): ["Arial Italic.ttf", "HelveticaNeue.ttc"],
        (True, True): ["Arial Bold Italic.ttf", "HelveticaNeue.ttc"],
    }
    candidates.extend(Path("/System/Library/Fonts/Supplemental") / name for name in mac_font_names[(bold, italic)])
    candidates.extend(Path("/System/Library/Fonts") / name for name in mac_font_names[(bold, italic)])
    return next((item for item in candidates if item.exists()), None)


def _font_name(bold: bool = False, italic: bool = False) -> str:
    return "AtelierSans" + ("Bold" if bold else "") + ("Italic" if italic else "")


def _base14_font_name(text: str, family: str | None, bold: bool, italic: bool) -> str | None:
    """Keep standard PDF font metrics when the replacement is ASCII-safe."""
    if any(ord(character) > 127 for character in text):
        return None
    family_key = (family or "").casefold()
    variants = {
        "helvetica": {(False, False): "helv", (True, False): "hebo", (False, True): "heit", (True, True): "hebi"},
        "times": {(False, False): "tiro", (True, False): "tibo", (False, True): "tiit", (True, True): "tibi"},
        "courier": {(False, False): "cour", (True, False): "cobo", (False, True): "coit", (True, True): "cobi"},
    }
    for marker, names in variants.items():
        if marker in family_key:
            return names[(bold, italic)]
    return None


def inspect_pdf(path: Path) -> dict:
    with fitz.open(path) as document:
        metadata = document.metadata or {}
        if document.needs_pass:
            return {
                "page_count": document.page_count,
                "pages": [],
                "metadata": metadata,
                "encrypted": True,
                "scanned_likely": False,
            }
        pages = []
        total_words = 0
        for index, page in enumerate(document):
            words = page.get_text("words")
            total_words += len(words)
            page_area = max(1.0, page.rect.width * page.rect.height)
            image_coverage = sum(
                max(0.0, rect.width * rect.height) / page_area
                for image in page.get_images(full=True)
                for rect in page.get_image_rects(image[0])
            )
            scanned_page = len(words) < 4 and image_coverage >= 0.2
            pages.append({
                "index": index,
                "number": index + 1,
                "width": page.rect.width,
                "height": page.rect.height,
                "rotation": page.rotation,
                "word_count": len(words),
                "scanned_likely": scanned_page,
            })
        return {
            "page_count": document.page_count,
            "pages": pages,
            "metadata": metadata,
            "encrypted": bool(document.needs_pass),
            "scanned_likely": any(page["scanned_likely"] for page in pages),
        }


def render_page(path: Path, page_index: int, scale: float = 1.5) -> bytes:
    with fitz.open(path) as document:
        if page_index < 0 or page_index >= document.page_count:
            raise IndexError("Sayfa bulunamadı")
        page = document[page_index]
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        return pixmap.tobytes("png")


def text_blocks(path: Path, page_index: int) -> list[dict]:
    with fitz.open(path) as document:
        page = document[page_index]
        result = []
        for block_index, block in enumerate(page.get_text("dict")["blocks"]):
            if block.get("type") != 0:
                continue
            # A PyMuPDF block may contain several unrelated table cells or
            # visually distant lines. Treating the whole block as one editable
            # object makes a small edit reflow all of them from the block's
            # top-left corner. Keep each real PDF span independent instead.
            for line_index, line in enumerate(block.get("lines", [])):
                for span_index, span in enumerate(line.get("spans", [])):
                    text = span.get("text", "")
                    if not text.strip():
                        continue
                    color_value = int(span.get("color", 0))
                    bbox = list(span.get("bbox", block["bbox"]))
                    origin = span.get("origin", (bbox[0], bbox[3]))
                    result.append({
                        "id": f"p{page_index}-b{block_index}-l{line_index}-s{span_index}",
                        "text": text,
                        "bbox": bbox,
                        "baseline": float(origin[1]),
                        "font": span.get("font", "Helvetica"),
                        "font_size": float(span.get("size", 11)),
                        "color": f"#{color_value:06x}",
                        "bold": bool(span.get("flags", 0) & 16),
                        "italic": bool(span.get("flags", 0) & 2),
                    })
        return result


def image_elements(path: Path, page_index: int) -> list[dict]:
    with fitz.open(path) as document:
        if page_index < 0 or page_index >= document.page_count:
            raise IndexError("Sayfa bulunamadı")
        page = document[page_index]
        result = []
        for index, info in enumerate(page.get_image_info(xrefs=True)):
            xref = int(info.get("xref") or 0)
            rect = fitz.Rect(info.get("bbox", (0, 0, 0, 0)))
            if xref <= 0 or rect.is_empty or not rect.intersects(page.rect):
                continue
            rect &= page.rect
            result.append({
                "id": f"p{page_index}-i{xref}-{index}",
                "xref": xref,
                "bbox": list(rect),
                "pixel_width": int(info.get("width") or 0),
                "pixel_height": int(info.get("height") or 0),
            })
        return result


def _normalized_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _matches_search(value: str, query: str, case_sensitive: bool, whole_word: bool) -> bool:
    candidate = _normalized_text(value)
    needle = _normalized_text(query)
    if not case_sensitive:
        candidate = candidate.casefold()
        needle = needle.casefold()
    if whole_word:
        return bool(re.fullmatch(rf"(?<!\w){re.escape(needle)}(?!\w)", candidate))
    return needle in candidate


def _search_rects(page: fitz.Page, query: str, case_sensitive: bool, whole_word: bool) -> list[fitz.Rect]:
    candidates = page.search_for(query, quads=False)
    return [
        fitz.Rect(rect) for rect in candidates
        if _matches_search(page.get_textbox(rect), query, case_sensitive, whole_word)
    ]


def search_text(path: Path, query: str, case_sensitive: bool = False,
                whole_word: bool = False, pages: list[int] | None = None) -> list[dict]:
    with fitz.open(path) as document:
        page_indexes = pages if pages is not None else list(range(document.page_count))
        if any(index < 0 or index >= document.page_count for index in page_indexes):
            raise ValueError("Aranacak sayfa numarası geçersiz")
        matches = []
        for page_index in page_indexes:
            page = document[page_index]
            for rect in _search_rects(page, query, case_sensitive, whole_word):
                matches.append({
                    "page": page_index,
                    "bbox": list(rect),
                    "text": _normalized_text(page.get_textbox(rect)),
                })
        return matches


def _span_style_at(page: fitz.Page, rect: fitz.Rect) -> dict:
    best: tuple[float, dict] | None = None
    for block in page.get_text("dict").get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                span_rect = fitz.Rect(span.get("bbox", (0, 0, 0, 0)))
                overlap = span_rect & rect
                score = max(0.0, overlap.width) * max(0.0, overlap.height)
                if score and (best is None or score > best[0]):
                    best = (score, span)
    span = best[1] if best else {}
    color_value = int(span.get("color", 0))
    return {
        "font_size": float(span.get("size", max(4.0, rect.height * 0.75))),
        "color": tuple(((color_value >> shift) & 255) / 255 for shift in (16, 8, 0)),
        "baseline": float(span.get("origin", (rect.x0, rect.y1 - 1))[1]),
    }


def replace_text(path: Path, output: Path, request) -> dict:
    with fitz.open(path) as document:
        page_indexes = request.pages if request.pages is not None else list(range(document.page_count))
        if any(index < 0 or index >= document.page_count for index in page_indexes):
            raise ValueError("Değiştirilecek sayfa numarası geçersiz")
        plan: dict[int, list[tuple[fitz.Rect, dict]]] = {}
        for page_index in page_indexes:
            page = document[page_index]
            matches = _search_rects(page, request.query, request.case_sensitive, request.whole_word)
            if matches:
                plan[page_index] = [(rect, _span_style_at(page, rect)) for rect in matches]

        replaced = sum(len(items) for items in plan.values())
        if replaced == 0:
            raise ValueError("Aranan metin bulunamadı")

        font_path = _unicode_font()
        for page_index, items in plan.items():
            page = document[page_index]
            for rect, _style in items:
                page.add_redact_annot(rect, fill=False)
            page.apply_redactions(
                images=fitz.PDF_REDACT_IMAGE_NONE,
                graphics=fitz.PDF_REDACT_LINE_ART_NONE,
            )
            if request.replacement:
                for rect, style in items:
                    page.insert_text(
                        (rect.x0, style["baseline"]),
                        request.replacement,
                        fontsize=style["font_size"],
                        fontname="AtelierSans" if font_path else "helv",
                        fontfile=str(font_path) if font_path else None,
                        color=style["color"],
                        overlay=True,
                    )
        document.save(output, garbage=4, deflate=True, clean=True)
    return {
        "matches": replaced,
        "pages_changed": len(plan),
        "method": "content-stream-redaction-rebuild",
    }


def _hex_to_rgb(value: str) -> tuple[float, float, float]:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))


def edit_text(path: Path, output: Path, request) -> dict:
    with fitz.open(path) as document:
        page = document[request.page]
        source_rect = fitz.Rect(*request.rect)
        target_rect = fitz.Rect(*(request.target_rect or request.rect))
        if not source_rect.intersects(page.rect) or source_rect.is_empty:
            raise ValueError("Metin alanı sayfa sınırları dışında")
        if not target_rect.intersects(page.rect) or target_rect.is_empty:
            raise ValueError("Yeni metin alanı sayfa sınırları dışında")
        source_rect &= page.rect
        target_rect &= page.rect

        # Redaction removes intersecting content operators from the content stream;
        # the old text is not merely covered by an overlay.
        page.add_redact_annot(source_rect, fill=False)
        page.apply_redactions(
            images=fitz.PDF_REDACT_IMAGE_NONE,
            graphics=fitz.PDF_REDACT_LINE_ART_NONE,
        )

        if request.text:
            base14_name = _base14_font_name(
                request.text, request.style.font_family,
                request.style.bold, request.style.italic,
            )
            font_path = None if base14_name else _unicode_font(
                request.style.bold, request.style.italic, request.style.font_family,
            )
            font_name = base14_name or (_font_name(request.style.bold, request.style.italic) if font_path else "helv")
            font = fitz.Font(fontfile=str(font_path)) if font_path else fitz.Font(font_name)
            lines = request.text.splitlines() or [request.text]
            line_height = request.style.font_size * 1.2
            baseline = (
                request.source_baseline + target_rect.y0 - source_rect.y0
                if request.source_baseline is not None
                else target_rect.y0 + request.style.font_size * 0.8
            )

            # insert_textbox applies its own ascender/descender padding and can
            # move short table values by a full line. Insert on the extracted
            # PDF baseline instead, so editing content does not change position.
            for line_index, line in enumerate(lines):
                line_baseline = baseline + line_index * line_height
                if line_baseline > page.rect.y1:
                    raise ValueError("Yeni metin sayfa sınırlarının dışına taşıyor")
                width = font.text_length(line, fontsize=request.style.font_size)
                if request.style.align == "right":
                    x = target_rect.x1 - width
                elif request.style.align == "center":
                    x = target_rect.x0 + (target_rect.width - width) / 2
                else:
                    x = target_rect.x0
                x = max(page.rect.x0, min(x, page.rect.x1 - min(width, page.rect.width)))
                page.insert_text(
                    (x, line_baseline),
                    line,
                    fontsize=request.style.font_size,
                    fontname=font_name,
                    fontfile=str(font_path) if font_path else None,
                    color=_hex_to_rgb(request.style.color),
                    overlay=True,
                )
                if request.style.underline and line:
                    underline_y = min(page.rect.y1, line_baseline + max(0.75, request.style.font_size * 0.08))
                    page.draw_line(
                        (x, underline_y), (min(page.rect.x1, x + width), underline_y),
                        color=_hex_to_rgb(request.style.color),
                        width=max(0.5, request.style.font_size / 16),
                        overlay=True,
                    )

        document.save(output, garbage=4, deflate=True, clean=True)

    raw = output.read_bytes()
    old_text_present = bool(request.original_text and request.original_text.encode("utf-8") in raw)
    return {"old_text_raw_bytes_present": old_text_present, "method": "content-stream-redaction-rebuild"}


def move_image(path: Path, output: Path, page_index: int, xref: int,
               source_values: tuple[float, float, float, float],
               target_values: tuple[float, float, float, float]) -> None:
    with fitz.open(path) as document:
        if page_index < 0 or page_index >= document.page_count:
            raise IndexError("Sayfa bulunamadı")
        page = document[page_index]
        source = fitz.Rect(*source_values)
        target = fitz.Rect(*target_values)
        if source.is_empty or not source.intersects(page.rect):
            raise ValueError("Kaynak görsel alanı geçersiz")
        if target.is_empty or not page.rect.contains(target):
            raise ValueError("Yeni görsel alanı sayfa sınırları dışında")
        source &= page.rect
        occurrences = page.get_image_rects(xref)
        if not any(abs(rect.x0 - source.x0) < 1 and abs(rect.y0 - source.y0) < 1 and
                   abs(rect.x1 - source.x1) < 1 and abs(rect.y1 - source.y1) < 1 for rect in occurrences):
            raise ValueError("Taşınacak görsel bu konumda bulunamadı")
        extracted = document.extract_image(xref)
        image_bytes = extracted.get("image")
        if not image_bytes:
            raise ValueError("Görsel verisi çıkarılamadı")

        # Kaynak görüntü çağrısı içerikten kaldırılır; metin ve vektörler korunur.
        page.add_redact_annot(source, fill=False)
        page.apply_redactions(
            images=fitz.PDF_REDACT_IMAGE_REMOVE,
            graphics=fitz.PDF_REDACT_LINE_ART_NONE,
            text=fitz.PDF_REDACT_TEXT_NONE,
        )
        page.insert_image(target, stream=image_bytes, keep_proportion=False, overlay=True)
        document.save(output, garbage=4, deflate=True, clean=True)


def rotate_pages(path: Path, output: Path, pages: list[int], angle: int) -> None:
    normalized = angle % 360
    if normalized not in {0, 90, 180, 270}:
        raise ValueError("Döndürme açısı 90 derecenin katı olmalıdır")
    with fitz.open(path) as document:
        for index in pages:
            document[index].set_rotation((document[index].rotation + normalized) % 360)
        document.save(output, garbage=4, deflate=True)


def parse_ranges(ranges: Iterable[str], page_count: int) -> list[list[int]]:
    groups = []
    for spec in ranges:
        pages: list[int] = []
        for token in re.split(r"\s*,\s*", spec.strip()):
            if not token:
                continue
            if "-" in token:
                start, end = (int(value) for value in token.split("-", 1))
                pages.extend(range(start - 1, end))
            else:
                pages.append(int(token) - 1)
        if not pages or any(page < 0 or page >= page_count for page in pages):
            raise ValueError(f"Geçersiz sayfa aralığı: {spec}")
        groups.append(pages)
    return groups


def split_pdf(path: Path, ranges: list[str]) -> list[tuple[str, bytes]]:
    reader = PdfReader(path)
    outputs = []
    for index, pages in enumerate(parse_ranges(ranges, len(reader.pages)), start=1):
        writer = PdfWriter()
        for page in pages:
            writer.add_page(reader.pages[page])
        buffer = io.BytesIO()
        writer.write(buffer)
        outputs.append((f"bolum-{index}.pdf", buffer.getvalue()))
    return outputs


def merge_pdfs(paths: list[Path], output: Path) -> None:
    writer = PdfWriter()
    for path in paths:
        reader = PdfReader(path)
        for page in reader.pages:
            writer.add_page(page)
    with output.open("wb") as handle:
        writer.write(handle)


def compress_pdf(path: Path, output: Path, level: str) -> dict:
    original_size = path.stat().st_size
    with fitz.open(path) as document:
        optimized_images = 0
        if level in {"balanced", "small"}:
            max_dimension = 1800 if level == "balanced" else 1200
            quality = 78 if level == "balanced" else 55
            processed: set[int] = set()
            for page in document:
                for image_info in page.get_images(full=True):
                    xref = image_info[0]
                    if xref in processed:
                        continue
                    processed.add(xref)
                    try:
                        extracted = document.extract_image(xref)
                        content = extracted.get("image", b"")
                        if len(content) < 40 * 1024:
                            continue
                        with Image.open(io.BytesIO(content)) as source:
                            if source.mode in {"RGBA", "LA"}:
                                continue
                            image = source.convert("RGB")
                            if max(image.size) > max_dimension:
                                image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
                            buffer = io.BytesIO()
                            image.save(buffer, format="JPEG", quality=quality, optimize=True, progressive=True)
                            replacement = buffer.getvalue()
                        if len(replacement) < len(content) * 0.92:
                            page.replace_image(xref, stream=replacement)
                            optimized_images += 1
                    except Exception:
                        continue
        document.save(output, garbage=4, deflate=True, clean=True, use_objstms=1)
    output_size = output.stat().st_size
    if output_size >= original_size:
        output.write_bytes(path.read_bytes())
        output_size = original_size
    return {
        "original_size": original_size,
        "output_size": output_size,
        "saved_bytes": original_size - output_size,
        "ratio": round((1 - output_size / original_size) * 100, 2) if original_size else 0,
        "level": level,
        "optimized_images": optimized_images,
        "note": "PDF nesneleri temizlendi; uygun gömülü görseller optimize edildi, sayfalar rasterize edilmedi.",
    }


def delete_pages(path: Path, output: Path, pages: list[int]) -> None:
    with fitz.open(path) as document:
        unique = sorted(set(pages), reverse=True)
        if any(index < 0 or index >= document.page_count for index in unique):
            raise ValueError("Silinecek sayfa numarası geçersiz")
        if len(unique) >= document.page_count:
            raise ValueError("Belgede en az bir sayfa kalmalıdır")
        for index in unique:
            document.delete_page(index)
        document.save(output, garbage=4, deflate=True, clean=True)


def reorder_pages(path: Path, output: Path, order: list[int]) -> None:
    with fitz.open(path) as document:
        expected = list(range(document.page_count))
        if sorted(order) != expected:
            raise ValueError("Yeni sıra bütün sayfaları tam olarak bir kez içermelidir")
        document.select(order)
        document.save(output, garbage=4, deflate=True, clean=True)


def crop_page(path: Path, output: Path, page_index: int, rect_values: tuple[float, float, float, float]) -> None:
    with fitz.open(path) as document:
        if page_index < 0 or page_index >= document.page_count:
            raise ValueError("Sayfa bulunamadı")
        page = document[page_index]
        rect = fitz.Rect(*rect_values)
        if rect.is_empty or not page.rect.contains(rect):
            raise ValueError("Kırpma alanı sayfa sınırları içinde olmalıdır")
        page.set_cropbox(rect)
        document.save(output, garbage=4, deflate=True, clean=True)


def add_blank_page(path: Path, output: Path, request) -> None:
    with fitz.open(path) as document:
        if request.after_page < -1 or request.after_page >= document.page_count:
            raise ValueError("Boş sayfa konumu geçersiz")
        reference = document[max(0, request.after_page)]
        width = request.width or reference.rect.width
        height = request.height or reference.rect.height
        document.new_page(pno=request.after_page + 1, width=width, height=height)
        document.save(output, garbage=4, deflate=True, clean=True)


def decorate_pages(path: Path, output: Path, request) -> None:
    if not request.header.strip() and not request.footer.strip() and not request.page_numbers:
        raise ValueError("En az bir üstbilgi, altbilgi veya sayfa numarası seçilmelidir")
    with fitz.open(path) as document:
        indexes = request.pages if request.pages is not None else list(range(document.page_count))
        if any(index < 0 or index >= document.page_count for index in indexes):
            raise ValueError("Üstbilgi/altbilgi sayfa numarası geçersiz")
        font_path = _unicode_font()
        font_name = _font_name() if font_path else "helv"
        color = _hex_to_rgb(request.color)
        for offset, page_index in enumerate(indexes):
            page = document[page_index]
            left = page.rect.x0 + request.margin
            right = page.rect.x1 - request.margin
            if right <= left:
                raise ValueError("Kenar boşluğu sayfa boyutu için çok büyük")
            if request.header.strip():
                page.insert_textbox(
                    fitz.Rect(left, page.rect.y0 + 8, right, page.rect.y0 + request.margin),
                    request.header.strip(), fontsize=request.font_size, fontname=font_name,
                    fontfile=str(font_path) if font_path else None, color=color,
                    align=fitz.TEXT_ALIGN_LEFT, overlay=True,
                )
            footer_top = page.rect.y1 - request.margin
            if request.footer.strip():
                page.insert_textbox(
                    fitz.Rect(left, footer_top, right, page.rect.y1 - 6),
                    request.footer.strip(), fontsize=request.font_size, fontname=font_name,
                    fontfile=str(font_path) if font_path else None, color=color,
                    align=fitz.TEXT_ALIGN_LEFT, overlay=True,
                )
            if request.page_numbers:
                number = request.start_number + offset
                page.insert_textbox(
                    fitz.Rect(left, footer_top, right, page.rect.y1 - 6), str(number),
                    fontsize=request.font_size, fontname=font_name,
                    fontfile=str(font_path) if font_path else None, color=color,
                    align=fitz.TEXT_ALIGN_RIGHT, overlay=True,
                )
        document.save(output, garbage=4, deflate=True, clean=True)


def _validated_rect(page: fitz.Page, values: tuple[float, float, float, float]) -> fitz.Rect:
    rect = fitz.Rect(*values)
    if rect.is_empty or rect.width < 1 or rect.height < 1 or not page.rect.intersects(rect):
        raise ValueError("Alan sayfa sınırları içinde ve pozitif boyutta olmalıdır")
    return rect & page.rect


def add_text(path: Path, output: Path, request) -> None:
    with fitz.open(path) as document:
        page = document[request.page]
        rect = _validated_rect(page, request.rect)
        alignments = {
            "left": fitz.TEXT_ALIGN_LEFT,
            "center": fitz.TEXT_ALIGN_CENTER,
            "right": fitz.TEXT_ALIGN_RIGHT,
            "justify": fitz.TEXT_ALIGN_JUSTIFY,
        }
        font_path = _unicode_font(request.style.bold, request.style.italic, request.style.font_family)
        result = page.insert_textbox(
            rect, request.text, fontsize=request.style.font_size,
            fontname=_font_name(request.style.bold, request.style.italic) if font_path else "helv",
            fontfile=str(font_path) if font_path else None,
            color=_hex_to_rgb(request.style.color),
            align=alignments[request.style.align],
        )
        if result < 0:
            raise ValueError("Metin seçilen alana sığmıyor")
        if request.style.underline:
            line_height = request.style.font_size * 1.2
            for line_index, line in enumerate(request.text.splitlines() or [request.text]):
                y = rect.y0 + line_height * (line_index + 1)
                if y >= rect.y1:
                    break
                width = min(rect.width, max(4, len(line) * request.style.font_size * 0.52))
                page.draw_line(
                    (rect.x0, y), (rect.x0 + width, y), color=_hex_to_rgb(request.style.color),
                    width=max(0.5, request.style.font_size / 16), overlay=True,
                )
        document.save(output, garbage=4, deflate=True, clean=True)


def add_shape(path: Path, output: Path, request) -> None:
    with fitz.open(path) as document:
        page = document[request.page]
        rect = _validated_rect(page, request.rect)
        stroke = _hex_to_rgb(request.stroke_color)
        fill = _hex_to_rgb(request.fill_color) if request.fill_color else None
        if request.kind == "rectangle":
            page.draw_rect(rect, color=stroke, fill=fill, width=request.width, overlay=True)
        elif request.kind == "ellipse":
            page.draw_oval(rect, color=stroke, fill=fill, width=request.width, overlay=True)
        else:
            page.draw_line(rect.top_left, rect.bottom_right, color=stroke, width=request.width, overlay=True)
        document.save(output, garbage=4, deflate=True, clean=True)


def add_ink(path: Path, output: Path, request) -> None:
    with fitz.open(path) as document:
        page = document[request.page]
        shape = page.new_shape()
        drawn = 0
        for raw_path in request.paths:
            if len(raw_path) < 2:
                continue
            points = [fitz.Point(x, y) for x, y in raw_path]
            if any(not page.rect.contains(point) for point in points):
                raise ValueError("Çizim noktaları sayfa sınırları içinde olmalıdır")
            shape.draw_polyline(points)
            drawn += 1
        if not drawn:
            raise ValueError("Çizim için en az iki nokta gereklidir")
        shape.finish(color=_hex_to_rgb(request.color), width=request.width, closePath=False)
        shape.commit(overlay=True)
        document.save(output, garbage=4, deflate=True, clean=True)


def add_watermark(path: Path, output: Path, request) -> None:
    if request.rotation not in {0, 90, 180, 270}:
        raise ValueError("Filigran dönüşü 0, 90, 180 veya 270 olmalıdır")
    with fitz.open(path) as document:
        indexes = request.pages if request.pages is not None else list(range(document.page_count))
        if any(index < 0 or index >= document.page_count for index in indexes):
            raise ValueError("Filigran sayfa numarası geçersiz")
        for index in indexes:
            page = document[index]
            height = min(page.rect.height * .25, request.font_size * 3)
            rect = fitz.Rect(page.rect.x0 + 24, page.rect.y0 + (page.rect.height - height) / 2,
                             page.rect.x1 - 24, page.rect.y0 + (page.rect.height + height) / 2)
            annot = page.add_freetext_annot(rect, request.text, fontsize=request.font_size,
                                           text_color=_hex_to_rgb(request.color), fill_color=None,
                                           align=fitz.TEXT_ALIGN_CENTER, rotate=request.rotation)
            annot.set_opacity(request.opacity)
            annot.set_info(subject="AtelierWatermark", title="Atelier Docs")
            annot.update()
        document.save(output, garbage=4, deflate=True, clean=True)


def remove_watermarks(path: Path, output: Path, pages: list[int] | None = None) -> None:
    with fitz.open(path) as document:
        indexes = pages if pages is not None else list(range(document.page_count))
        if any(index < 0 or index >= document.page_count for index in indexes):
            raise ValueError("Filigran sayfa numarası geçersiz")
        removed = 0
        for index in indexes:
            page = document[index]
            annot = page.first_annot
            while annot:
                next_annot = annot.next
                if (annot.info or {}).get("subject") == "AtelierWatermark":
                    page.delete_annot(annot); removed += 1
                annot = next_annot
        if not removed:
            raise ValueError("Atelier Docs ile eklenmiş kaldırılabilir filigran bulunamadı")
        document.save(output, garbage=4, deflate=True, clean=True)


def add_link(path: Path, output: Path, request) -> None:
    if not request.uri.lower().startswith(("https://", "http://", "mailto:")):
        raise ValueError("Bağlantı http, https veya mailto ile başlamalıdır")
    with fitz.open(path) as document:
        page = document[request.page]
        rect = _validated_rect(page, request.rect)
        page.insert_link({"kind": fitz.LINK_URI, "from": rect, "uri": request.uri})
        document.save(output, garbage=4, deflate=True, clean=True)


def redact_areas(path: Path, output: Path, page_index: int,
                 rect_values: list[tuple[float, float, float, float]]) -> dict:
    with fitz.open(path) as document:
        page = document[page_index]
        rects = [_validated_rect(page, values) for values in rect_values]
        before_text = page.get_text()
        for rect in rects:
            page.add_redact_annot(rect, fill=(0, 0, 0), text="")
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)
        after_text = page.get_text()
        document.save(output, garbage=4, deflate=True, clean=True)
        return {"areas": len(rects), "removed_characters": max(0, len(before_text) - len(after_text))}


def add_image(path: Path, output: Path, page_index: int,
              rect_values: tuple[float, float, float, float], image_path: Path) -> None:
    with fitz.open(path) as document:
        page = document[page_index]
        rect = _validated_rect(page, rect_values)
        page.insert_image(rect, filename=str(image_path), keep_proportion=True, overlay=True)
        document.save(output, garbage=4, deflate=True, clean=True)


def encrypt_pdf(path: Path, output: Path, request) -> None:
    with fitz.open(path) as document:
        if document.needs_pass:
            raise ValueError("PDF zaten şifreli")
        permissions = fitz.PDF_PERM_ACCESSIBILITY
        if request.allow_print:
            permissions |= fitz.PDF_PERM_PRINT | fitz.PDF_PERM_PRINT_HQ
        if request.allow_copy:
            permissions |= fitz.PDF_PERM_COPY
        if request.allow_annotate:
            permissions |= fitz.PDF_PERM_ANNOTATE
        document.save(
            output,
            encryption=fitz.PDF_ENCRYPT_AES_256,
            owner_pw=request.owner_password or request.user_password,
            user_pw=request.user_password,
            permissions=permissions,
            garbage=4,
            deflate=True,
        )


def unlock_pdf(path: Path, output: Path, password: str) -> None:
    with fitz.open(path) as document:
        if not document.needs_pass:
            raise ValueError("PDF şifreli değil")
        if document.authenticate(password) <= 0:
            raise ValueError("PDF parolası geçersiz")
        document.save(output, encryption=fitz.PDF_ENCRYPT_NONE, garbage=4, deflate=True)


def update_metadata(path: Path, output: Path, request) -> None:
    with fitz.open(path) as document:
        if document.needs_pass:
            raise ValueError("Metadata düzenlemek için önce PDF kilidini açın")
        existing = document.metadata or {}
        existing.update({
            "title": request.title,
            "author": request.author,
            "subject": request.subject,
            "keywords": request.keywords,
        })
        document.set_metadata(existing)
        document.save(output, garbage=4, deflate=True, clean=True)
