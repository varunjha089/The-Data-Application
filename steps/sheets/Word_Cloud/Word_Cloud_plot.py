"""Plot of the sheet "Word_Cloud": a word cloud of the keywords (the size of a word follows the number of papers that use it)
Input : Word_Cloud.csv in this folder (run Word_Cloud.py first)        Output: word_cloud (.png and .svg, same folder)
Layout: the most used keyword is placed first (at most 70 % of the width), near the middle of an oval; each next one goes to the free spot nearest the middle (a quarter of them
        written upwards). A word that does not fit is made smaller, and left out only below the smallest size; a word is never larger than a more used one. Font size = largest size *
        (papers / papers of the top keyword) ^ 0.6, so a keyword used half as often is not drawn half as large. Colours: blue, violet, green, pink, red,
        teal and indigo (no yellow or orange, which are hard to read on white). The words are drawn as outlines, so they stay sharp in the SVG.
Your choices: --words N (default 150): how many keywords are drawn; --leave-out N (default 0): leave out the N most used keywords first, e.g. the words
        of your search, which are in nearly every paper and would fill the picture (they stay in the table).
Run   : python3 Word_Cloud_plot.py [--words 150] [--leave-out 0]   (needs matplotlib, numpy, pandas)
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.font_manager import FontProperties
from matplotlib.patches import PathPatch
from matplotlib.textpath import TextPath
from matplotlib.transforms import Affine2D

HERE = Path(__file__).resolve().parent
COLORS = ["#1F5FAD", "#6A3D9A", "#2E7D32", "#C2185B", "#C62828", "#00838F", "#303F9F", "#8E24AA"]
W, H, CELL = 1600, 1000, 4                                         # the canvas (drawing units) and the cell of the grid that marks what is taken
FONT = FontProperties(family="DejaVu Sans", weight="bold")

ap = argparse.ArgumentParser(description="Plot of the sheet Word_Cloud")
ap.add_argument("--words", type=int, default=150, help="how many of the most used keywords are drawn (default 150)")
ap.add_argument("--leave-out", type=int, default=0, help="leave out the N most used keywords (e.g. the search terms; default 0)")
args = ap.parse_args()

t = pd.read_csv(HERE / "Word_Cloud.csv", encoding="utf-8-sig", keep_default_na=False, na_values=[""]).dropna(subset=["Keyword"])
out = t.head(max(0, args.leave_out))
top = t.iloc[len(out):].head(max(1, args.words))
rng = np.random.default_rng(7)                                     # the same data always gives the same picture

gw, gh = W // CELL, H // CELL
yy, xx = np.mgrid[0:gh, 0:gw]
taken = ((xx + 0.5 - gw / 2) / (gw / 2)) ** 2 + ((yy + 0.5 - gh / 2) / (gh / 2)) ** 2 > 1     # outside the oval counts as taken
centre = np.hypot((xx - gw / 2) / gw, (yy - gh / 2) / gh)


def free_spots(w, h):
    """the grid positions (lower-left cell) where a w x h block of cells is completely free"""
    s = np.pad(taken.astype(np.int32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    if h > gh or w > gw:
        return np.zeros((0, 0), bool)
    return (s[h:, w:] - s[:-h, w:] - s[h:, :-w] + s[:-h, :-w]) == 0


fmax, small = float(top["Papers"].iloc[0]), H * 0.012
big = min(H * 0.16, 0.7 * W / TextPath((0, 0), str(top["Keyword"].iloc[0]), size=1, prop=FONT).get_extents().width)   # the top word: at most 70 % of the width
last = big                                                         # the size of the last word drawn: a less used word is never drawn larger
placed = []
for word, n in zip(top["Keyword"], top["Papers"]):
    upright = rng.random() < 0.25 and len(placed) > 0
    size = max(min(big * (n / fmax) ** 0.6, last), small)
    path = TextPath((0, 0), str(word), size=1, prop=FONT)
    if upright:
        path = path.transformed(Affine2D().rotate_deg(90))
    ext = path.get_extents()
    while size >= small:
        pad = max(1, int(round(size * 0.08 / CELL)))           # free space around the word (cells), larger for larger words
        w, h = int(np.ceil(ext.width * size / CELL)) + 2 * pad, int(np.ceil(ext.height * size / CELL)) + 2 * pad
        ok = free_spots(w, h)
        if ok.any():
            gy, gx = np.nonzero(ok)
            d = centre[np.minimum(gy + h // 2, gh - 1), np.minimum(gx + w // 2, gw - 1)] + rng.random(len(gx)) * 0.02
            i = int(np.argmin(d))
            taken[gy[i]:gy[i] + h, gx[i]:gx[i] + w] = True
            shift = Affine2D().scale(size).translate((gx[i] + pad) * CELL - ext.x0 * size, (gy[i] + pad) * CELL - ext.y0 * size)
            placed.append((path.transformed(shift), COLORS[int(rng.integers(len(COLORS)))]))
            last = size
            break
        size *= 0.9

fig, ax = plt.subplots(figsize=(12, 7.9))
for p, c in placed:
    ax.add_patch(PathPatch(p, facecolor=c, edgecolor="none"))
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.set_aspect("equal")
ax.axis("off")
left = f"; {len(top) - len(placed)} did not fit" if len(placed) < len(top) else ""
ax.set_title(f"Word cloud of the keywords (the {len(placed)} most used of {len(t):,}{left}; size = number of papers)", fontweight="bold")
if len(out):
    ax.text(0.5, -0.01, "Left out (the most used): " + ", ".join(f"{k} ({n:,})" for k, n in zip(out["Keyword"], out["Papers"])), transform=ax.transAxes,
            ha="center", va="top", fontsize=10, color="#555555", wrap=True)
for ext in ("png", "svg"):
    fig.savefig(HERE / f"word_cloud.{ext}", dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"{len(placed)} keywords drawn (the most used: {top['Keyword'].iloc[0]}, {int(fmax)} papers)")
print("written word_cloud.png and word_cloud.svg")
