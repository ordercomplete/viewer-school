#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Генерація ресурсів інсталятора: app.ico, wizard.png, wizard-small.png.

Запуск:  python installer/make_assets.py
Потрібен Pillow (тільки на етапі збірки; для роботи застосунку не потрібен).
Файли кладуться в installer/ і використовуються скриптом viewer_setup.iss.
"""
import io
import sys
from pathlib import Path
from typing import cast

from PIL import Image, ImageDraw, ImageFont

cast(io.TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
NAVY = (26, 58, 107)
BLUE = (44, 90, 160)
WHITE = (255, 255, 255)
GOLD = (232, 182, 76)
FONT_BOLD = r"C:\Windows\Fonts\segoeuib.ttf"
FONT_REG = r"C:\Windows\Fonts\segoeui.ttf"


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return cast(ImageFont.FreeTypeFont, ImageFont.load_default(size))


def gradient(size: tuple[int, int], top: tuple[int, int, int],
             bottom: tuple[int, int, int]) -> Image.Image:
    """Вертикальний градієнт top → bottom."""
    w, h = size
    img = Image.new("RGB", size)
    px = img.load()
    assert px is not None
    for y in range(h):
        k = y / max(1, h - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * k) for i in range(3))
        for x in range(w):
            px[x, y] = color
    return img


def draw_sheet(dr: ImageDraw.ImageDraw, size: int, fill: tuple = WHITE) -> None:
    """Малює «аркуш із текстом» — основу логотипа."""
    m = size * 0.24
    top = size * 0.21
    bottom = size - m * 0.86
    dr.rounded_rectangle([m, top, size - m, bottom],
                         radius=size * 0.06, fill=fill)
    lx0, lx1 = m + size * 0.07, size - m - size * 0.07
    for i, frac in enumerate((0.34, 0.47, 0.60)):
        x1 = lx1 - (size * 0.13 if i == 2 else 0)
        y = size * frac
        dr.rounded_rectangle([lx0, y, x1, y + size * 0.045],
                             radius=size * 0.022, fill=BLUE)
    dr.rectangle([size * 0.60, top, size * 0.72, size * 0.50], fill=GOLD)


def app_icon(size: int) -> Image.Image:
    """Іконка застосунку: заокруглений квадрат + аркуш."""
    ss = 4                                   # надвибірка для гладких країв
    img = Image.new("RGBA", (size * ss, size * ss), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    pad = size * ss * 0.055
    dr.rounded_rectangle([pad, pad, size * ss - pad, size * ss - pad],
                         radius=size * ss * 0.22, fill=NAVY)
    draw_sheet(dr, size * ss)
    return img.resize((size, size), Image.Resampling.LANCZOS)


def wrap(text: str, fnt: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    words, lines, line = text.split(), [], ""
    for word in words:
        probe = f"{line} {word}".strip()
        if fnt.getlength(probe) <= max_w or not line:
            line = probe
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def wizard_image() -> Image.Image:
    """Банер візарда 240×459 (співвідношення 164:314)."""
    w, h = 240, 459
    img = gradient((w, h), NAVY, BLUE).convert("RGBA")
    dr = ImageDraw.Draw(img)

    # Аркуш-логотип
    logo = app_icon(96).resize((96, 96), Image.Resampling.LANCZOS)
    img.alpha_composite(logo, (int(w / 2 - 48), 58))

    fb48 = font(FONT_BOLD, 26)
    fb20 = font(FONT_BOLD, 18)
    fr16 = font(FONT_REG, 16)

    y = 190
    for line in wrap("Viewer-for-School", fb48, w - 44):
        dr.text((w / 2, y), line, font=fb48, fill=WHITE, anchor="ma")
        y += 32

    y += 6
    dr.line([w * 0.25, y, w * 0.75, y], fill=GOLD, width=2)
    y += 18

    for line in wrap("Переглядач навчальних матеріалів", fr16, w - 40):
        dr.text((w / 2, y), line, font=fr16, fill=(226, 234, 246), anchor="ma")
        y += 22

    y += 10
    for line in wrap("11-Д · 2026–2027", fb20, w - 40):
        dr.text((w / 2, y), line, font=fb20, fill=GOLD, anchor="ma")
        y += 24

    dr.text((w / 2, h - 26), "FileViewer-for-students-and-teachers",
            font=font(FONT_REG, 10), fill=(198, 212, 232), anchor="md")
    return img


def wizard_small() -> Image.Image:
    """Малий банер візарда 150×57 (WizardStyle=modern)."""
    w, h = 150, 57
    img = Image.new("RGBA", (w, h), NAVY + (255,))
    dr = ImageDraw.Draw(img)
    logo = app_icon(48).resize((40, 40), Image.Resampling.LANCZOS)
    img.alpha_composite(logo, (6, 9))
    fb = font(FONT_BOLD, 13)
    fr = font(FONT_REG, 10)
    dr.text((52, 14), "Viewer-for-", font=fb, fill=WHITE)
    dr.text((52, 28), "School", font=fb, fill=GOLD)
    dr.text((52, 43), "11-Д · матеріали", font=fr, fill=(208, 220, 238))
    return img


def main() -> int:
    ico = app_icon(256)
    ico.save(HERE / "app.ico",
             sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                    (64, 64), (128, 128), (256, 256)])
    wizard_image().save(HERE / "wizard.png")
    wizard_small().save(HERE / "wizard-small.png")
    for name in ("app.ico", "wizard.png", "wizard-small.png"):
        path = HERE / name
        print(f"  {name:<18} {path.stat().st_size:>7} Б")
    print("Ресурси інсталятора готові:", HERE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
