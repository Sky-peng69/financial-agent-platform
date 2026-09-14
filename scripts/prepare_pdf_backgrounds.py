from pathlib import Path
from PIL import Image

ROOT = Path("docs/competition/assets")
names = [
    "body-background-icbc-ai.png",
    "body-background-research-evidence.png",
    "body-background-ai-orchestration.png",
]
paper = Image.new("RGB", (1536, 2048), (250, 249, 246))

for name in names:
    source = Image.open(ROOT / name).convert("RGB").resize(paper.size, Image.Resampling.LANCZOS)
    result = Image.new("RGB", paper.size)
    pixels = result.load()
    source_pixels = source.load()
    for x in range(paper.width):
        # 左侧留白区几乎不显图，右侧逐渐保留视觉主体
        progress = x / (paper.width - 1)
        alpha = 0.035 + 0.25 * max(0.0, (progress - 0.28) / 0.72)
        for y in range(paper.height):
            r, g, b = source_pixels[x, y]
            pixels[x, y] = tuple(round(base * (1 - alpha) + value * alpha) for base, value in zip(paper.getpixel((0, 0)), (r, g, b)))
    Image.fromarray if False else None
    output = ROOT / name.replace(".png", "-pdf.png")
    result.save(output, optimize=True)
