from __future__ import annotations

import io
import math
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


def convert_image(
    path: Path,
    output_format: str,
    quality: int = 86,
    background: str = "#ffffff",
    max_width: int | None = None,
    max_height: int | None = None,
) -> tuple[bytes, dict]:
    output_format = output_format.upper()
    if output_format not in {"JPEG", "PNG", "WEBP"}:
        raise ValueError("Çıktı biçimi JPEG, PNG veya WEBP olmalıdır")
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image)
        original_size = image.size
        if max_width is not None and max_width <= 0 or max_height is not None and max_height <= 0:
            raise ValueError("Görsel genişliği ve yüksekliği sıfırdan büyük olmalıdır")
        if max_width or max_height:
            image.thumbnail((max_width or image.width, max_height or image.height), Image.Resampling.LANCZOS)
        if output_format == "JPEG" and image.mode in {"RGBA", "LA", "P"}:
            backdrop = Image.new("RGB", image.size, background)
            if image.mode != "RGBA":
                image = image.convert("RGBA")
            backdrop.paste(image, mask=image.getchannel("A"))
            image = backdrop
        elif output_format == "JPEG":
            image = image.convert("RGB")
        elif output_format == "WEBP":
            image = image.convert("RGBA" if "A" in image.getbands() or image.mode == "P" and "transparency" in image.info else "RGB")
        elif output_format == "PNG" and image.mode == "CMYK":
            image = image.convert("RGB")
        buffer = io.BytesIO()
        options = {"format": output_format, "optimize": True}
        if output_format in {"JPEG", "WEBP"}:
            options["quality"] = max(1, min(100, quality))
        if image.info.get("icc_profile"):
            options["icc_profile"] = image.info["icc_profile"]
        if image.info.get("dpi"):
            options["dpi"] = image.info["dpi"]
        image.save(buffer, **options)
        return buffer.getvalue(), {"original_dimensions": original_size, "output_dimensions": image.size}


def edit_image(path: Path, *, brightness: float = 1, contrast: float = 1, saturation: float = 1,
               grayscale: bool = False, sepia: bool = False, blur: float = 0, sharpen: float = 0,
               rotate: int = 0, flip: str = "none", crop_x: int = 0, crop_y: int = 0,
               crop_width: int | None = None, crop_height: int | None = None) -> bytes:
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGBA")
        if crop_width is not None or crop_height is not None:
            width = crop_width if crop_width is not None else image.width - crop_x
            height = crop_height if crop_height is not None else image.height - crop_y
            if crop_x < 0 or crop_y < 0 or width <= 0 or height <= 0 or crop_x + width > image.width or crop_y + height > image.height:
                raise ValueError("Kırpma alanı görsel sınırları içinde olmalıdır")
            image = image.crop((crop_x, crop_y, crop_x + width, crop_y + height))
        image = ImageEnhance.Brightness(image).enhance(brightness)
        image = ImageEnhance.Contrast(image).enhance(contrast)
        image = ImageEnhance.Color(image).enhance(saturation)
        if grayscale:
            image = ImageOps.grayscale(image).convert("RGBA")
        if sepia:
            alpha = image.getchannel("A")
            gray = ImageOps.grayscale(image)
            image = ImageOps.colorize(gray, "#3b2414", "#f4ddb0").convert("RGBA")
            image.putalpha(alpha)
        if blur > 0:
            image = image.filter(ImageFilter.GaussianBlur(blur))
        if sharpen > 0:
            image = ImageEnhance.Sharpness(image).enhance(1 + min(5, sharpen))
        if rotate:
            image = image.rotate(-rotate, expand=True)
        if flip == "horizontal":
            image = ImageOps.mirror(image)
        elif flip == "vertical":
            image = ImageOps.flip(image)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue()


def compress_to_target(
    path: Path,
    target_kb: int,
    output_format: str = "JPEG",
    max_width: int | None = None,
    max_height: int | None = None,
) -> tuple[bytes, dict]:
    output_format = output_format.upper()
    if output_format not in {"JPEG", "WEBP"}:
        raise ValueError("Hedef boyut sıkıştırması JPEG veya WEBP destekler")
    if target_kb < 10 or target_kb > 100 * 1024:
        raise ValueError("Hedef boyut 10 KB ile 100 MB arasında olmalıdır")
    target_bytes = target_kb * 1024

    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        if max_width or max_height:
            image.thumbnail((max_width or image.width, max_height or image.height), Image.Resampling.LANCZOS)

        def encode(quality: int) -> bytes:
            buffer = io.BytesIO()
            image.save(buffer, format=output_format, quality=quality, optimize=True)
            return buffer.getvalue()

        minimum = encode(5)
        resize_steps = 0
        while len(minimum) > target_bytes and min(image.size) > 128 and resize_steps < 8:
            ratio = min(0.9, max(0.35, math.sqrt(target_bytes / len(minimum)) * 0.94))
            next_size = (max(128, int(image.width * ratio)), max(128, int(image.height * ratio)))
            if next_size == image.size:
                break
            image = image.resize(next_size, Image.Resampling.LANCZOS)
            minimum = encode(5)
            resize_steps += 1

        best: bytes | None = None
        best_quality = 5
        low, high = 5, 95
        while low <= high:
            quality = (low + high) // 2
            content = encode(quality)
            if len(content) <= target_bytes:
                best, best_quality = content, quality
                low = quality + 1
            else:
                high = quality - 1

        if best is None:
            best = minimum
            best_quality = 5

        return best, {
            "target_bytes": target_bytes,
            "output_bytes": len(best),
            "quality": best_quality,
            "target_reached": len(best) <= target_bytes,
            "dimensions": image.size,
            "resize_steps": resize_steps,
        }
