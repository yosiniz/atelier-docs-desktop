from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw


def main() -> None:
    output = Path(__file__).resolve().parent / "fixtures"
    output.mkdir(parents=True, exist_ok=True)

    pdf_path = output / "atelier-ornek.pdf"
    document = pymupdf.open()
    for number in range(1, 3):
        page = document.new_page(width=595, height=842)
        page.draw_rect((46, 48, 549, 790), color=(0.82, 0.84, 0.9), width=1)
        page.insert_text((72, 96), "ATELIER DOCS", fontsize=22, color=(0.24, 0.2, 0.65))
        page.insert_text((72, 142), f"Örnek belge — Sayfa {number}", fontsize=16)
        page.insert_text((72, 186), "Bu metin düzenlenebilir bir PDF içerik bloğudur.", fontsize=12)
        page.insert_text((72, 212), "Türkçe karakterler: ç, ğ, ı, İ, ö, ş, ü", fontsize=12)
        page.insert_text((72, 750), "Yerel işlem • Dosyalar cihazınızda kalır", fontsize=10, color=(0.35, 0.38, 0.45))
    document.save(pdf_path)
    document.close()

    image_path = output / "atelier-ornek.png"
    image = Image.new("RGB", (1000, 700), "#11182b")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((90, 90, 910, 610), radius=36, fill="#6d5dfc")
    draw.text((150, 270), "ATELIER DOCS — IMAGE QA", fill="white")
    image.save(image_path)

    print(pdf_path)
    print(image_path)


if __name__ == "__main__":
    main()
