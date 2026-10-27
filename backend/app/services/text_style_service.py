"""Estimate the visible ink style of scanned text, not its invisible OCR font."""
from functools import lru_cache
from pathlib import Path

import cv2
import fitz
import numpy as np


def _candidates():
    roots = [Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype/dejavu"),
             Path("/System/Library/Fonts/Supplemental")]
    variants = [
        ("Arial", False, False, ["arial.ttf", "DejaVuSans.ttf", "Arial.ttf"]),
        ("Arial", True, False, ["arialbd.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"]),
        ("Arial", False, True, ["ariali.ttf", "DejaVuSans-Oblique.ttf", "Arial Italic.ttf"]),
        ("Times New Roman", False, False, ["times.ttf", "DejaVuSerif.ttf", "Times New Roman.ttf"]),
        ("Times New Roman", True, False, ["timesbd.ttf", "DejaVuSerif-Bold.ttf", "Times New Roman Bold.ttf"]),
    ]
    for family, bold, italic, names in variants:
        path = next((root / name for root in roots for name in names if (root / name).is_file()), None)
        if path:
            yield family, bold, italic, path


@lru_cache(maxsize=64)
def _template(text: str, path: str):
    font = fitz.Font(fontfile=path)
    width = max(100, font.text_length(text, fontsize=40) + 20)
    with fitz.open() as document:
        page = document.new_page(width=width, height=90)
        page.insert_text((10, 60), text, fontsize=40, fontname="Sample", fontfile=path)
        pix = page.get_pixmap(matrix=fitz.Matrix(3, 3), colorspace=fitz.csGRAY, alpha=False)
        mask = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width) < 160
        y, x = np.where(mask)
        if not len(x):
            return None
        return mask[y.min():y.max()+1, x.min():x.max()+1].astype(np.uint8), float(y.max()+1-y.min()) / 3, float(y.max()+1) / 3 - 60


def scan_text_style(page: fitz.Page, rect: fitz.Rect, original_text: str) -> dict:
    scale = min(4.0, (2_000_000 / max(1, rect.get_area())) ** .5)
    clip = (rect + (-.6, -.6, .6, .6)) & page.rect
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip, colorspace=fitz.csRGB, alpha=False)
    rgb = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, 3)
    if rgb.size == 0:
        raise ValueError("Metnin görüntüsü okunamadı")
    border = np.concatenate((rgb[0, :, :], rgb[-1, :, :], rgb[:, 0, :], rgb[:, -1, :]), axis=0)
    background = np.median(border, axis=0)
    distance = np.max(np.abs(rgb.astype(float) - background), axis=2).astype(np.uint8)
    threshold, mask = cv2.threshold(distance, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    foreground = (mask > 0) & (distance > max(12, threshold))
    ys, xs = np.where(foreground)
    if len(xs) < 5:
        return {"font_size": max(4, rect.height / .75), "font_family": "Arial", "color": "#333333",
                "bold": False, "italic": False, "baseline": rect.y1, "estimated": True}
    # Antialiased border pixels are lighter than the actual ink. Sample the
    # strongest half of the foreground rather than averaging with the paper.
    core = foreground & (distance >= np.percentile(distance[foreground], 50))
    ink = np.median(rgb[core], axis=0).astype(int)
    observed = foreground[ys.min():ys.max()+1, xs.min():xs.max()+1].astype(np.uint8)
    best = None
    for family, bold, italic, path in _candidates():
        template = _template(original_text[:200], str(path))
        if template is None:
            continue
        bitmap, height, descender = template
        normalized = cv2.resize(bitmap, (observed.shape[1], observed.shape[0]), interpolation=cv2.INTER_NEAREST)
        intersection = float(np.logical_and(normalized, observed).sum())
        score = 2 * intersection / max(1, normalized.sum() + observed.sum())
        if best is None or score > best[0]:
            best = (score, family, bold, italic, height, descender)
    _, family, bold, italic, reference_height, descender = best or (0, "Arial", False, False, 30, 0)
    size = (ys.max()+1-ys.min()) / scale * 40 / reference_height
    baseline = clip.y0 + (ys.max()+1) / scale - descender * size / 40
    return {"font_size": round(max(4.0, min(144.0, size)), 2), "font_family": family,
            "color": "#" + "".join(f"{value:02x}" for value in ink), "bold": bold, "italic": italic,
            "baseline": float(baseline), "estimated": True,
            "background_color": "#" + "".join(f"{int(value):02x}" for value in background)}


def source_text_style(page: fitz.Page, rect: fitz.Rect, original_text: str) -> dict:
    is_ocr = any(trace.get("type") == 3 and (rect & fitz.Rect(trace["bbox"])).get_area() > rect.get_area() * .5
                 for trace in page.get_texttrace())
    if is_ocr:
        return scan_text_style(page, rect, original_text)
    best = None
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                area = (rect & fitz.Rect(span["bbox"])).get_area()
                if area > 0 and (best is None or area > best[0]):
                    best = area, span
    if not best:
        raise ValueError("Kaynak metin biçimi bulunamadı")
    span = best[1]
    return {"font_size": span["size"], "font_family": span["font"], "color": f'#{span["color"]:06x}',
            "bold": bool(span["flags"] & 16), "italic": bool(span["flags"] & 2),
            "baseline": span["origin"][1], "estimated": False}
