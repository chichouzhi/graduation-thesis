from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def strip_ansi(text: str) -> str:
    import re

    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--title", default="")
    parser.add_argument("--subtitle", default="")
    parser.add_argument("--max-lines", type=int, default=34)
    args = parser.parse_args()

    raw = Path(args.input).read_text(encoding="utf-8", errors="replace")
    lines = strip_ansi(raw).splitlines()
    if len(lines) > args.max_lines:
        head = lines[: max(6, args.max_lines // 2)]
        tail = lines[-(args.max_lines - len(head) - 1) :]
        lines = head + ["..."] + tail

    font_body = load_font(20)

    width = 1800
    line_height = 31
    padding = 44
    height = padding * 2 + line_height * max(1, len(lines))

    image = Image.new("RGB", (width, height), "#0f172a")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((18, 18, width - 18, height - 18), radius=10, fill="#0f172a", outline="#334155", width=2)
    y = padding
    for line in lines:
        draw.text((44, y), line[:150], font=font_body, fill="#e5e7eb")
        y += line_height

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output)


if __name__ == "__main__":
    main()
