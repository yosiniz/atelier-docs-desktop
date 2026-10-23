from __future__ import annotations

import html
import io
import zipfile
from copy import deepcopy
from pathlib import Path

import pymupdf
from docx import Document
from docx.enum.section import WD_SECTION
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor as DocxRGBColor
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from PIL import Image, ImageOps
from pptx import Presentation
from pptx.dml.color import RGBColor as PptxRGBColor
from pptx.enum.text import MSO_ANCHOR
from pptx.util import Pt as PptxPt

from .native_office_service import office_to_pdf_native
from .pdf_service import _unicode_font


def _clean_word_font_name(value: str | None) -> str:
    name = (value or "Arial").split("+", 1)[-1]
    lowered = name.casefold()
    if "helvetica" in lowered or "arial" in lowered:
        return "Arial"
    if "times" in lowered or "serif" in lowered:
        return "Times New Roman"
    if "courier" in lowered or "mono" in lowered:
        return "Courier New"
    return name.replace("-BoldItalic", "").replace("-Bold", "").replace("-Italic", "").replace("-Oblique", "")


def _remove_paragraph_content(paragraph) -> None:
    for child in list(paragraph._p):
        if child.tag != qn("w:pPr"):
            paragraph._p.remove(child)


def _configure_pdf_page_section(section, page_rect: pymupdf.Rect) -> None:
    section.page_width = Pt(page_rect.width)
    section.page_height = Pt(page_rect.height)
    section.top_margin = Pt(0)
    section.bottom_margin = Pt(0)
    section.left_margin = Pt(0)
    section.right_margin = Pt(0)
    section.header_distance = Pt(0)
    section.footer_distance = Pt(0)


def _textless_page_png(source: pymupdf.Document, page_index: int, dpi: int = 144) -> bytes:
    background = pymupdf.open()
    try:
        background.insert_pdf(source, from_page=page_index, to_page=page_index)
        page = background[0]
        for block in page.get_text("dict").get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    rect = pymupdf.Rect(span.get("bbox", (0, 0, 0, 0)))
                    if not rect.is_empty:
                        page.add_redact_annot(rect, fill=False)
        page.apply_redactions(
            images=pymupdf.PDF_REDACT_IMAGE_NONE,
            graphics=pymupdf.PDF_REDACT_LINE_ART_NONE,
            text=pymupdf.PDF_REDACT_TEXT_REMOVE,
        )
        scale = dpi / 72
        return page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False).tobytes("png")
    finally:
        background.close()


def _add_page_background(section, image: bytes, width: float, height: float) -> None:
    header = section.header
    header.is_linked_to_previous = False
    paragraph = header.paragraphs[0]
    _remove_paragraph_content(paragraph)
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = Pt(1)
    shape = paragraph.add_run().add_picture(io.BytesIO(image), width=Pt(width), height=Pt(height))
    inline = shape._inline
    anchor = OxmlElement("wp:anchor")
    for key, value in {
        "distT": "0", "distB": "0", "distL": "0", "distR": "0",
        "simplePos": "0", "relativeHeight": "0", "behindDoc": "1",
        "locked": "0", "layoutInCell": "1", "allowOverlap": "1",
    }.items():
        anchor.set(key, value)

    simple_position = OxmlElement("wp:simplePos")
    simple_position.set("x", "0")
    simple_position.set("y", "0")
    anchor.append(simple_position)
    horizontal = OxmlElement("wp:positionH")
    horizontal.set("relativeFrom", "page")
    horizontal_offset = OxmlElement("wp:posOffset")
    horizontal_offset.text = "0"
    horizontal.append(horizontal_offset)
    anchor.append(horizontal)
    vertical = OxmlElement("wp:positionV")
    vertical.set("relativeFrom", "page")
    vertical_offset = OxmlElement("wp:posOffset")
    vertical_offset.text = "0"
    vertical.append(vertical_offset)
    anchor.append(vertical)
    anchor.append(deepcopy(inline.extent))
    effect_extent = OxmlElement("wp:effectExtent")
    for edge in ("l", "t", "r", "b"):
        effect_extent.set(edge, "0")
    anchor.append(effect_extent)
    anchor.append(OxmlElement("wp:wrapNone"))
    anchor.append(deepcopy(inline.docPr))
    non_visual = inline.find(qn("wp:cNvGraphicFramePr"))
    if non_visual is not None:
        anchor.append(deepcopy(non_visual))
    anchor.append(deepcopy(inline.graphic))
    inline.getparent().replace(inline, anchor)


def _add_positioned_span(document: Document, span: dict) -> None:
    text = span.get("text", "")
    if not text.strip():
        return
    x0, y0, x1, y1 = (float(value) for value in span.get("bbox", (0, 0, 0, 0)))
    size = max(4.0, min(144.0, float(span.get("size", 11))))
    width = max(size, x1 - x0 + max(2.0, size * 0.18))
    height = max(y1 - y0 + 2.0, size * 1.28)

    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = Pt(size)
    paragraph_properties = paragraph._p.get_or_add_pPr()
    frame = OxmlElement("w:framePr")
    attributes = {
        "w:w": round(width * 20),
        "w:h": round(height * 20),
        "w:x": round(x0 * 20),
        "w:y": round(y0 * 20),
        "w:hAnchor": "page",
        "w:vAnchor": "page",
        "w:wrap": "none",
        "w:hRule": "exact",
    }
    for key, value in attributes.items():
        frame.set(qn(key), str(value))
    paragraph_properties.append(frame)

    run = paragraph.add_run(text)
    flags = int(span.get("flags", 0))
    run.bold = bool(flags & 16)
    run.italic = bool(flags & 2)
    run.font.size = Pt(size)
    font_name = _clean_word_font_name(span.get("font"))
    run.font.name = font_name
    run_properties = run._element.get_or_add_rPr()
    run_fonts = run_properties.get_or_add_rFonts()
    run_fonts.set(qn("w:ascii"), font_name)
    run_fonts.set(qn("w:hAnsi"), font_name)
    run_fonts.set(qn("w:cs"), font_name)
    color = int(span.get("color", 0))
    run.font.color.rgb = DocxRGBColor((color >> 16) & 255, (color >> 8) & 255, color & 255)


def pdf_to_docx(path: Path, output: Path) -> dict:
    """Preserve PDF geometry with editable, page-anchored Word text frames."""
    document = Document()
    if document.paragraphs:
        first = document.paragraphs[0]
        first._element.getparent().remove(first._element)

    span_count = 0
    with pymupdf.open(path) as source:
        if source.page_count == 0:
            raise ValueError("PDF içinde sayfa bulunamadı")
        for page_index, page in enumerate(source):
            section = document.sections[0] if page_index == 0 else document.add_section(WD_SECTION.NEW_PAGE)
            _configure_pdf_page_section(section, page.rect)
            _add_page_background(
                section,
                _textless_page_png(source, page_index),
                page.rect.width,
                page.rect.height,
            )
            for block in page.get_text("dict").get("blocks", []):
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        if span.get("text", "").strip():
                            _add_positioned_span(document, span)
                            span_count += 1

    document.save(output)
    return {
        "mode": "editable-positioned-layout",
        "positioned_text_spans": span_count,
        "warning": "Metinler düzenlenebilir ve PDF koordinatlarında tutulur; döndürülmüş/eğri metinler Word içinde sadeleştirilebilir.",
    }


def pdf_to_xlsx(path: Path, output: Path) -> dict:
    """Create an editable coordinate grid plus a lossless visual reference per page."""
    workbook = Workbook()
    default = workbook.active
    workbook.remove(default)
    with pymupdf.open(path) as source:
        for page_index, page in enumerate(source, start=1):
            reference = workbook.create_sheet(f"Görünüm {page_index}")
            reference.sheet_view.showGridLines = False
            reference["A1"] = "Kaynak PDF sayfasının kayıpsız görünümü"
            reference["A1"].font = Font(bold=True, color="334155")
            reference["A1"].fill = PatternFill("solid", fgColor="E2E8F0")
            reference.row_dimensions[1].height = 24
            from openpyxl.drawing.image import Image as SpreadsheetImage
            snapshot = page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False).tobytes("png")
            image = SpreadsheetImage(io.BytesIO(snapshot))
            image.width = page.rect.width * 1.5
            image.height = page.rect.height * 1.5
            reference.add_image(image, "A3")
            reference.sheet_properties.pageSetUpPr.fitToPage = True
            reference.page_setup.fitToWidth = 1
            reference.page_setup.fitToHeight = 1

            sheet = workbook.create_sheet(f"Sayfa {page_index}")
            sheet.sheet_view.showGridLines = False
            sheet.freeze_panes = "A1"
            unit_x = 7.0
            unit_y = 7.0
            max_column = max(1, int(page.rect.width / unit_x) + 2)
            max_row = max(1, int(page.rect.height / unit_y) + 2)
            for column in range(1, max_column + 1):
                sheet.column_dimensions[sheet.cell(1, column).column_letter].width = 1.0
            for row in range(1, max_row + 1):
                sheet.row_dimensions[row].height = unit_y

            span_count = 0
            for block in page.get_text("dict").get("blocks", []):
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = str(span.get("text", ""))
                        if not text.strip():
                            continue
                        x0, y0, _x1, _y1 = (float(value) for value in span.get("bbox", (0, 0, 0, 0)))
                        row = max(1, int(y0 / unit_y) + 1)
                        column = max(1, int(x0 / unit_x) + 1)
                        cell = sheet.cell(row, column)
                        if cell.value:
                            row += 1
                            cell = sheet.cell(row, column)
                        cell.value = text
                        flags = int(span.get("flags", 0))
                        color = int(span.get("color", 0))
                        cell.font = Font(
                            name=_clean_word_font_name(span.get("font")),
                            size=max(4.0, min(72.0, float(span.get("size", 11)))),
                            bold=bool(flags & 16),
                            italic=bool(flags & 2),
                            color=f"{color & 0xFFFFFF:06X}",
                        )
                        cell.alignment = Alignment(vertical="top", wrap_text=False)
                        span_count += 1
    workbook.save(output)
    return {
        "mode": "editable-coordinate-grid-with-reference",
        "warning": "Sayfa görünümü ayrı bir referans sekmesinde korunur; PDF metinleri koordinatlarına yakın düzenlenebilir hücrelere aktarılır.",
    }


def pdf_to_pptx(path: Path, output: Path) -> dict:
    """Preserve the PDF page appearance while keeping every text span editable."""
    presentation = Presentation()
    presentation.slides._sldIdLst.clear()
    span_count = 0
    with pymupdf.open(path) as source:
        if source.page_count:
            presentation.slide_width = int(source[0].rect.width * 12700)
            presentation.slide_height = int(source[0].rect.height * 12700)
        for page_index, page in enumerate(source):
            slide = presentation.slides.add_slide(presentation.slide_layouts[6])
            scale_x = (presentation.slide_width / 12700) / page.rect.width
            scale_y = (presentation.slide_height / 12700) / page.rect.height
            slide.shapes.add_picture(
                io.BytesIO(_textless_page_png(source, page_index)),
                0,
                0,
                width=presentation.slide_width,
                height=presentation.slide_height,
            )
            for block in page.get_text("dict").get("blocks", []):
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = str(span.get("text", ""))
                        if not text.strip():
                            continue
                        x0, y0, x1, y1 = (float(value) for value in span.get("bbox", (0, 0, 0, 0)))
                        size = max(4.0, min(72.0, float(span.get("size", 11))))
                        width = max(size, x1 - x0 + max(2.0, size * 0.22))
                        height = max(y1 - y0 + 2.0, size * 1.3)
                        shape = slide.shapes.add_textbox(
                            int(x0 * scale_x * 12700),
                            int(y0 * scale_y * 12700),
                            max(1, int(width * scale_x * 12700)),
                            max(1, int(height * scale_y * 12700)),
                        )
                        frame = shape.text_frame
                        frame.clear()
                        frame.word_wrap = False
                        frame.margin_left = 0
                        frame.margin_right = 0
                        frame.margin_top = 0
                        frame.margin_bottom = 0
                        frame.vertical_anchor = MSO_ANCHOR.TOP
                        paragraph = frame.paragraphs[0]
                        paragraph.space_before = PptxPt(0)
                        paragraph.space_after = PptxPt(0)
                        run = paragraph.add_run()
                        run.text = text
                        run.font.name = _clean_word_font_name(span.get("font"))
                        run.font.size = PptxPt(size * min(scale_x, scale_y))
                        flags = int(span.get("flags", 0))
                        run.font.bold = bool(flags & 16)
                        run.font.italic = bool(flags & 2)
                        color = int(span.get("color", 0))
                        run.font.color.rgb = PptxRGBColor((color >> 16) & 255, (color >> 8) & 255, color & 255)
                        span_count += 1
    presentation.save(output)
    return {
        "mode": "editable-positioned-layout",
        "positioned_text_spans": span_count,
        "warning": "Sayfa çizimleri arka planda korunur; metinler PDF koordinatlarında düzenlenebilir kutulardır.",
    }


def pdf_to_images(path: Path, output_format: str = "png", dpi: int = 144, quality: int = 88) -> bytes:
    output_format = output_format.lower()
    if output_format not in {"png", "jpg", "jpeg"}:
        raise ValueError("Görsel biçimi PNG veya JPG olmalıdır")
    if dpi < 72 or dpi > 360:
        raise ValueError("DPI 72 ile 360 arasında olmalıdır")

    archive = io.BytesIO()
    with pymupdf.open(path) as document, zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        matrix = pymupdf.Matrix(dpi / 72, dpi / 72)
        extension = "jpg" if output_format in {"jpg", "jpeg"} else "png"
        for index, page in enumerate(document, start=1):
            # A PDF page is composited onto an opaque white page by default. Exporting
            # a transparent alpha channel made valid pages appear dark or washed out
            # in some PNG viewers, so both PNG and JPG use the same RGB render.
            pixmap = page.get_pixmap(matrix=matrix, colorspace=pymupdf.csRGB, alpha=False)
            if extension == "png":
                content = pixmap.tobytes("png")
            else:
                image = Image.open(io.BytesIO(pixmap.tobytes("png"))).convert("RGB")
                buffer = io.BytesIO()
                image.save(buffer, format="JPEG", quality=max(30, min(100, quality)), optimize=True)
                content = buffer.getvalue()
            bundle.writestr(f"sayfa-{index:04d}.{extension}", content)
    archive.seek(0)
    return archive.getvalue()


def images_to_pdf(paths: list[Path], output: Path) -> dict:
    if not paths:
        raise ValueError("En az bir görsel gereklidir")
    pages: list[Image.Image] = []
    try:
        for path in paths:
            with Image.open(path) as source:
                image = ImageOps.exif_transpose(source)
                if image.mode in {"RGBA", "LA", "P"}:
                    rgba = image.convert("RGBA")
                    backdrop = Image.new("RGB", rgba.size, "white")
                    backdrop.paste(rgba, mask=rgba.getchannel("A"))
                    image = backdrop
                else:
                    image = image.convert("RGB")
                pages.append(image.copy())
        pages[0].save(output, format="PDF", save_all=True, append_images=pages[1:], resolution=144)
    finally:
        for image in pages:
            image.close()
    return {"page_count": len(paths), "mode": "image-pages"}


def docx_to_pdf(path: Path, output: Path) -> dict:
    """Prefer Word's native renderer, then use the deterministic local fallback."""
    native = office_to_pdf_native(path, output)
    if native is not None:
        return native

    source = Document(path)
    pdf = pymupdf.open()
    font_path = _unicode_font()
    page = pdf.new_page(width=595, height=842)
    y = 58.0
    margin = 56.0
    line_height = 15.0

    def add_line(value: str, size: float = 11) -> None:
        nonlocal page, y
        for logical_line in (value.splitlines() or [""]):
            words = logical_line.split(" ")
            current = ""
            for word in words or [""]:
                candidate = f"{current} {word}".strip()
                if len(candidate) > 88 and current:
                    write(current, size)
                    current = word
                else:
                    current = candidate
            write(current, size)

    def write(value: str, size: float) -> None:
        nonlocal page, y
        if y > page.rect.height - 58:
            page = pdf.new_page(width=595, height=842)
            y = 58.0
        page.insert_text(
            (margin, y), value or " ", fontsize=size,
            fontname="AtelierSans" if font_path else "helv",
            fontfile=str(font_path) if font_path else None,
            color=(0.08, 0.1, 0.16),
        )
        y += line_height * max(1, size / 11)

    for paragraph in source.paragraphs:
        if paragraph.text.strip():
            size = 16 if paragraph.style and paragraph.style.name.startswith("Heading") else 11
            add_line(paragraph.text, size)
            y += 5
    for table in source.tables:
        y += 5
        for row in table.rows:
            add_line(" | ".join(cell.text.replace("\n", " ") for cell in row.cells), 9)
        y += 7

    pdf.save(output, garbage=4, deflate=True)
    pdf.close()
    return {
        "mode": "local-text-fallback",
        "warning": "LibreOffice bulunmadığı için gelişmiş Word yerleşimleri ve üstbilgi/altbilgiler sınırlı işlenir.",
    }
