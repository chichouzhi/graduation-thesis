from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
CAPTURES = ROOT / "captures"
OUT = ROOT / "exported" / "图4-5-前端核心页面截图.png"


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def crop_view(path: Path) -> Image.Image:
    img = Image.open(path).convert("RGB")
    w, h = img.size
    crop_h = min(h, int(w * 0.58))
    return img.crop((0, 0, w, crop_h))


def main() -> None:
    panels = [
        CAPTURES / "图4-5-dashboard.png",
        CAPTURES / "图4-5-topics.png",
        CAPTURES / "图4-5-documents.png",
        CAPTURES / "图4-5-taskboard.png",
    ]

    canvas_w = 2200
    canvas_h = 1320
    margin = 44
    gap = 28
    panel_w = (canvas_w - margin * 2 - gap) // 2
    panel_h = (canvas_h - margin * 2 - gap) // 2

    canvas = Image.new("RGB", (canvas_w, canvas_h), "#ffffff")
    draw = ImageDraw.Draw(canvas)

    positions = [
        (margin, margin),
        (margin + panel_w + gap, margin),
        (margin, margin + panel_h + gap),
        (margin + panel_w + gap, margin + panel_h + gap),
    ]

    for path, (x, y) in zip(panels, positions):
        img = crop_view(path)
        img.thumbnail((panel_w - 20, panel_h - 20), Image.Resampling.LANCZOS)
        draw.rounded_rectangle(
            (x, y, x + panel_w, y + panel_h),
            radius=12,
            fill="#f8fafc",
            outline="#cbd5e1",
            width=2,
        )
        ix = x + (panel_w - img.width) // 2
        iy = y + (panel_h - img.height) // 2
        canvas.paste(img, (ix, iy))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT)


if __name__ == "__main__":
    main()
