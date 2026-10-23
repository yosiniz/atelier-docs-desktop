from pathlib import Path

from PIL import Image, ImageDraw


size = 1024
canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(canvas)

# Atelier Docs arayüzündeki mor kimliği ve üst üste belge fikrini taşır.
draw.rounded_rectangle((52, 52, 972, 972), radius=220, fill=(97, 79, 238, 255))
draw.rounded_rectangle((108, 92, 916, 928), radius=180, fill=(126, 108, 255, 255))

paper = (246, 247, 255, 255)
draw.rounded_rectangle((292, 214, 790, 826), radius=72, fill=(47, 37, 137, 90))
draw.rounded_rectangle((236, 168, 734, 780), radius=72, fill=paper)

# Katlanmış köşe.
draw.polygon([(590, 168), (734, 312), (590, 312)], fill=(207, 210, 255, 255))
draw.line([(590, 168), (590, 312), (734, 312)], fill=(158, 151, 246, 255), width=20)

# Belge satırları.
for y, width in [(404, 326), (492, 278), (580, 326)]:
    draw.rounded_rectangle((322, y, 322 + width, y + 34), radius=17, fill=(104, 91, 218, 255))
draw.rounded_rectangle((322, 668, 518, 702), radius=17, fill=(124, 113, 232, 255))

# Sağ altta ayrı katmanda düzenleme kalemi.
pencil = Image.new("RGBA", (430, 200), (0, 0, 0, 0))
pencil_draw = ImageDraw.Draw(pencil)
pencil_draw.rounded_rectangle((25, 55, 310, 145), radius=42, fill=(255, 196, 74, 255))
pencil_draw.polygon([(294, 55), (388, 100), (294, 145)], fill=(255, 237, 202, 255))
pencil_draw.polygon([(382, 91), (417, 100), (382, 109)], fill=(62, 52, 128, 255))
pencil = pencil.rotate(-34, resample=Image.Resampling.BICUBIC, expand=True)
canvas.alpha_composite(pencil, (535, 536))

output = Path(__file__).resolve().parents[1] / "assets" / "app-icon.ico"
canvas.save(output, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print(output)
