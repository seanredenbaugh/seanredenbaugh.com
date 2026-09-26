#!/usr/bin/env python3
"""Draws the SR favicon (dark square, white S, red R) at every size the site uses.
Needs Roboto Condensed Bold (TTF or WOFF); pass its path as the first argument."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONT = sys.argv[1] if len(sys.argv) > 1 else "roboto-condensed-latin-700-normal.woff"
OUT = Path(__file__).resolve().parent.parent / "static"
NIGHT, RED, WHITE = (28, 32, 41, 255), (217, 29, 35, 255), (255, 255, 255, 255)


def icon(size):
    S = size * 8
    im = Image.new("RGBA", (S, S), NIGHT)
    d = ImageDraw.Draw(im)
    fs = int(S * 0.74)
    f = ImageFont.truetype(FONT, fs)
    bb = d.textbbox((0, 0), "SR", font=f)
    f = ImageFont.truetype(FONT, int(fs * min(S * 0.80 / (bb[2] - bb[0]), S * 0.66 / (bb[3] - bb[1]))))
    bb = d.textbbox((0, 0), "SR", font=f)
    x = (S - (bb[2] - bb[0])) / 2 - bb[0]
    y = S / 2 - (bb[3] - bb[1]) / 2 - bb[1]
    d.text((x, y), "S", font=f, fill=WHITE)
    d.text((x + d.textlength("S", font=f), y), "R", font=f, fill=RED)
    return im.resize((size, size), Image.LANCZOS)


icon(512).save(OUT / "favicon-512.png")
icon(180).save(OUT / "apple-touch-icon.png")
icon(32).save(OUT / "favicon-32.png")
icon(64).save(OUT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
print("favicons written to", OUT)
