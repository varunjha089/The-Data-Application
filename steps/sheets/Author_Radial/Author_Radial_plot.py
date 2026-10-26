"""Plot of the sheet "Author_Radial": a radial bar chart of the leading authors (the style of the "Best Countries" overall-rankings chart).
One bar per author, sorted clockwise by rank starting on the left; the length of a bar is the author's fractional score; the colour is the author's country
(the countries with most authors get their own colour, equal counts by the better rank; the others are grey). Next to each bar: rank, name, and "fractional score · publications". Inside the
ring, the authors are grouped by rank (1-10, 11-20, ...): a line from the centre to each group and curved lines from the group to its bars.
Colours: blue, violet, green, pink, red, teal, indigo, sky blue, magenta (no yellow or orange). Background: --background dark (default) or light (for print).
Input : Author_Radial.csv in this folder (run Author_Radial.py first)        Output: author_radial (.png and .svg, same folder)
Run   : python3 Author_Radial_plot.py [--background dark|light] [--colours 12]   (needs matplotlib, numpy, pandas)
"""
import argparse
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Circle, PathPatch, Polygon
from matplotlib.path import Path as MPath

HERE = Path(__file__).resolve().parent
PALETTE = ["#4F9DDE", "#A07CD8", "#5CBF7A", "#E46FA8", "#E5604F", "#3DBFC0", "#7C8CF0", "#8FD3F5", "#C65BCF", "#2E7D32", "#1F5FAD", "#C2185B"]
R0, LENGTH, SPAN = 1.0, 1.05, 330.0          # inner radius, length of the longest bar, degrees covered (the rest is the gap on the left, below rank 1)

ap = argparse.ArgumentParser(description="Plot of the sheet Author_Radial")
ap.add_argument("--background", choices=["dark", "light"], default="dark")
ap.add_argument("--colours", type=int, default=12, help="how many countries get their own colour (the others are grey; default 12)")
args = ap.parse_args()
dark = args.background == "dark"
BG, INK, MUTED, LINE = ("#0B0B0F", "#F2F2F2", "#B8BCC4", "#5A5F6A") if dark else ("#FFFFFF", "#1A1A1A", "#555555", "#B8B8B8")
OTHER = "#7E8590" if dark else "#B5B9C0"

t = pd.read_csv(HERE / "Author_Radial.csv", encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype={"Author ID": str})
n = len(t)
if n == 0:
    raise SystemExit("No author in Author_Radial.csv: generate the data first.")
order = t["Country"].value_counts()
best = t.groupby("Country")["Rank"].min()
coloured = sorted([c for c in order.index if c != "Unknown"], key=lambda c: (-order[c], best[c]))[:max(0, args.colours)]   # most authors first, then the best rank
colour = {c: PALETTE[i % len(PALETTE)] for i, c in enumerate(coloured)}
score = t["Fractional score"].astype(float).to_numpy()
top = score.max() if score.max() > 0 else 1.0
step = SPAN / max(n - 1, 1)
angles = np.radians(180.0 - np.arange(n) * step)          # rank 1 on the left, then clockwise (over the top)
width = 0.62 * R0 * math.radians(step) if n > 1 else 0.05
fs = max(5.5, min(11.0, 520.0 / n))

fig, ax = plt.subplots(figsize=(15, 15))
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)
ax.set_aspect("equal")
ax.axis("off")

# the bars and their labels
for i, (a, r) in enumerate(zip(angles, t.itertuples(index=False))):
    length = max(LENGTH * score[i] / top, 0.02)
    u, v = np.array([math.cos(a), math.sin(a)]), np.array([-math.sin(a), math.cos(a)])
    p0, p1 = u * R0, u * (R0 + length)
    c = colour.get(r.Country, OTHER)
    ax.add_patch(Polygon([p0 - v * width / 2, p1 - v * width / 2, p1 + v * width / 2, p0 + v * width / 2], closed=True, facecolor=c, edgecolor="none"))
    deg = math.degrees(a)
    left = math.cos(a) < 0
    rot = deg + 180 if left else deg
    lp = u * (R0 + length + 0.03)
    ax.text(lp[0], lp[1], f"{r.Rank}. {r.Author}", rotation=rot, rotation_mode="anchor", ha="right" if left else "left", va="center",
            fontsize=fs, fontweight="bold", color=c)
    ip = u * (R0 + 0.03)                                       # score · publications, written inside the bar's base
    ax.text(ip[0], ip[1], f"{float(r[5]):.2f} · {int(r.Publications)}", rotation=rot, rotation_mode="anchor", ha="right" if left else "left",
            va="center", fontsize=fs * 0.72, color=BG if length > 0.25 else INK)

# the groups of ten ranks inside the ring: centre -> group -> bars
groups = [list(range(s, min(s + 10, n))) for s in range(0, n, 10)]
for g in groups:
    mid = (angles[g[0]] + angles[g[-1]]) / 2
    node = np.array([math.cos(mid), math.sin(mid)]) * R0 * 0.42
    ax.plot([0, node[0]], [0, node[1]], color=LINE, lw=1.0, zorder=1)
    for i in g:
        end = np.array([math.cos(angles[i]), math.sin(angles[i])]) * R0 * 0.985
        ctrl = np.array([math.cos(angles[i]), math.sin(angles[i])]) * R0 * 0.62
        ax.add_patch(PathPatch(MPath([node, ctrl, end], [MPath.MOVETO, MPath.CURVE3, MPath.CURVE3]), facecolor="none", edgecolor=LINE, lw=0.6, zorder=1))
    ax.add_patch(Circle(node, 0.018, facecolor=INK, edgecolor="none", zorder=3))
    deg = math.degrees(mid)
    left = math.cos(mid) < 0
    ax.text(node[0], node[1], f"  Rank {g[0] + 1}-{g[-1] + 1}  ", rotation=deg + 180 if left else deg, rotation_mode="anchor",
            ha="right" if left else "left", va="center", fontsize=9, color=INK, zorder=4)
ax.add_patch(Circle((0, 0), 0.012, facecolor=LINE, edgecolor="none", zorder=2))

lim = R0 + LENGTH + 0.75
ax.set_xlim(-lim, lim)
ax.set_ylim(-lim, lim)

# how to read, and the colours of the countries
how = [f"There are {n} bars, one for each author.", "The longer the bar, the higher the fractional score",
       "(each paper counts 1, shared by its authors).", "Authors are sorted clockwise by rank, starting on the left.",
       "Colour = the country the author publishes from.", "Numbers: fractional score · publications."]
fig.text(0.05, 0.955, "How to read", fontsize=14, fontweight="bold", color=INK, va="top")
fig.text(0.05, 0.93, "\n".join(how), fontsize=10.5, color=MUTED, va="top", linespacing=1.5)
fig.text(0.70, 0.955, "Country", fontsize=14, fontweight="bold", color=INK, va="top")
entries = [(c, colour[c], int(order[c])) for c in coloured] + ([("Other countries", OTHER, int(sum(order[c] for c in order.index if c not in colour)))]
                                                             if any(c not in colour for c in order.index) else [])
for k, (name, col, cnt) in enumerate(entries):
    x, y = 0.70 + (k // 6) * 0.15, 0.93 - (k % 6) * 0.022
    fig.patches.append(Circle((x + 0.005, y - 0.006), 0.005, transform=fig.transFigure, facecolor=col, edgecolor="none"))
    fig.text(x + 0.015, y, f"{name} ({cnt})", fontsize=10, color=INK, va="top")
ax.set_title(f"The {n} leading authors by fractional score", color=INK, fontsize=16, fontweight="bold")
for ext in ("png", "svg"):
    fig.savefig(HERE / f"author_radial.{ext}", dpi=150, bbox_inches="tight", facecolor=BG)
plt.close(fig)
print(f"{n} authors drawn; colours for {', '.join(coloured)}" + (" and grey for the other countries" if len(entries) > len(coloured) else ""))
print("written author_radial.png and author_radial.svg")
