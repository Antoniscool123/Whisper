"""Generate the original OpenFlow waveform icon (no external artwork)."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "openflow" / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)
image = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((8, 8, 504, 504), radius=112, fill="#10232E", outline="#315C60", width=8)
for x, height, color in ((104, 112, "#3BA99C"), (172, 216, "#52D4BF"), (240, 308, "#7CF3D9"),
                         (308, 216, "#52D4BF"), (376, 112, "#3BA99C")):
    draw.rounded_rectangle((x, 256 - height // 2, x + 32, 256 + height // 2), radius=16, fill=color)
image.resize((256, 256), Image.Resampling.LANCZOS).save(ASSETS / "icon.png")
image.save(ASSETS / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><rect x="8" y="8" width="496" height="496" rx="112" fill="#10232E" stroke="#315C60" stroke-width="8"/>'
for x, height, color in ((104,112,"#3BA99C"),(172,216,"#52D4BF"),(240,308,"#7CF3D9"),(308,216,"#52D4BF"),(376,112,"#3BA99C")):
    svg += f'<rect x="{x}" y="{256-height//2}" width="32" height="{height}" rx="16" fill="{color}"/>'
svg += '</svg>'
(ASSETS / "icon.svg").write_text(svg, encoding="utf-8")
print("Generated icon.png, icon.ico and icon.svg")
