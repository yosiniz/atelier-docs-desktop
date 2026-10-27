"""OCR-only image corrections; coordinates are mapped back to the untouched scan."""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image


MAX_PIXELS = 24_000_000


def prepare_scan(image: Image.Image, *, enhance: bool, deskew: bool, table: bool):
    original_width, original_height = image.size
    scale = min(1.0, (MAX_PIXELS / max(1, original_width * original_height)) ** 0.5)
    if scale < 1:
        image = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))))
    gray = np.asarray(image.convert("L"))
    if min(gray.shape) < 8:
        return Image.fromarray(gray), np.array([[1 / scale, 0, 0], [0, 1 / scale, 0]], dtype=float), 0.0
    # Estimate small skew from long, nearly horizontal edges (print lines/table
    # borders). Ignore vertical borders and handwriting strokes.
    angle = 0.0
    if deskew:
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 1800, threshold=80,
                                minLineLength=max(80, gray.shape[1] // 6), maxLineGap=20)
        angles = []
        if lines is not None:
            for x0, y0, x1, y1 in lines[:, 0]:
                candidate = float(np.degrees(np.arctan2(y1 - y0, x1 - x0)))
                if abs(candidate) <= 7:
                    angles.append(candidate)
        if len(angles) >= 3:
            angle = float(np.median(angles))
            if abs(angle) < 0.15:
                angle = 0.0
    rotation = cv2.getRotationMatrix2D((gray.shape[1] / 2, gray.shape[0] / 2), angle, 1)
    if angle:
        gray = cv2.warpAffine(gray, rotation, (gray.shape[1], gray.shape[0]),
                              flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=255)
    inverse = cv2.invertAffineTransform(rotation) / scale
    if enhance:
        # Remove slow illumination changes without sharpening scanner noise.
        background = cv2.GaussianBlur(gray, (0, 0), 25)
        normalized = cv2.divide(gray, np.maximum(background, 1), scale=255)
        gray = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8)).apply(normalized)
    if table:
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY_INV, 35, 15)
        horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN,
                                      cv2.getStructuringElement(cv2.MORPH_RECT, (max(40, gray.shape[1] // 25), 1)))
        vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN,
                                    cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(40, gray.shape[0] // 25))))
        mask = cv2.bitwise_or(horizontal, vertical)
        gray = cv2.inpaint(gray, mask, 2, cv2.INPAINT_TELEA)
    return Image.fromarray(gray), inverse, angle


def original_rect(left: int, top: int, width: int, height: int, inverse) -> tuple[float, float, float, float]:
    corners = np.array([[left, top, 1], [left + width, top, 1],
                        [left, top + height, 1], [left + width, top + height, 1]], dtype=float)
    points = corners @ inverse.T
    return float(points[:, 0].min()), float(points[:, 1].min()), float(points[:, 0].max()), float(points[:, 1].max())
