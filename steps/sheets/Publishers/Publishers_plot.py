"""Plot of the sheet "Publishers": one treemap per publisher, for the publishers with the most documents (default 4, in a grid (a), (b), ...).
Inside a publisher's panel every source is a rectangle whose area is its number of documents; the label gives the source, its documents and its share of the
publisher's documents (%). The largest source has the panel's own colour; the others are coloured by size: 10 % or more of the publisher, 2 or more documents,
1 document (grey). Sources beyond --tiles are put together in one rectangle "Other sources". Papers without a Source title (books, some
proceedings) are not a source, so they are not drawn (as in Bradford's law); their number is given under the panel's title. A name that does not fit is replaced by the source's
abbreviation (Abbreviated Source Title), then by its numbers only; the labels are drawn as outlines sized to their rectangle, so they never spill over.
Layout: the squarified treemap of Bruls, Huizing and van Wijk (2000): rectangles as close to squares as possible, the largest at the top left.
Input : Publishers.csv and Publishers_sources.csv in this folder (run Publishers.py first)        Output: publisher_treemaps (.png and .svg, same folder)
Run   : python3 Publishers_plot.py [--publishers 4] [--tiles 12]   (needs matplotlib, pandas)
"""
import argparse
import math
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.font_manager import FontProperties
from matplotlib.patches import PathPatch, Rectangle
from matplotlib.textpath import TextPath
from matplotlib.transforms import Affine2D

HERE = Path(__file__).resolve().parent
PANEL = ["#8CC5A8", "#EB9C7A", "#B9D97A", "#F5DA6A", "#9DB7E0", "#C9A3D9", "#F2A7B8", "#8FD0D6", "#D9C27A"]    # the largest source of panel a, b, c, ...
BIG, MID, ONE, OTHER = "#F5DA6A", "#E3CBA4", "#C4C4C4", "#DADADA"   # >= 10 % of the publisher, >= 2 documents, 1 document, "Other sources"
W, H = 460, 330                                                     # a panel in points (1/72 inch): a label of size s is s points high
NAME = FontProperties(family="DejaVu Serif", style="italic")
PLAIN = FontProperties(family="DejaVu Serif")

ap = argparse.ArgumentParser(description="Plot of the sheet Publishers")
ap.add_argument("--publishers", type=int, default=4, help="how many publishers get a panel (the ones with most documents; default 4)")
ap.add_argument("--tiles", type=int, default=12, help="most sources drawn in a panel; the others form one rectangle (default 12)")
args = ap.parse_args()


def read(name):
    return pd.read_csv(HERE / name, encoding="utf-8-sig", keep_default_na=False, na_values=[""])


def squarify(sizes, x, y, w, h):
    """rectangles (x, y, w, h) for sizes sorted from large to small, filling the box; y grows upwards, the first rectangle is at the top left"""
    total = float(sum(sizes))
    areas = [s * w * h / total for s in sizes]
    out = []

    def worst(row, side):
        s = sum(row)
        return max(max(side * side * a / (s * s), s * s / (side * side * a)) for a in row)

    while areas:
        side = min(w, h)
        row = [areas.pop(0)]
        while areas and worst(row + [areas[0]], side) <= worst(row, side):
            row.append(areas.pop(0))
        s = sum(row)
        if w >= h:                                          # a column on the left, filled from the top
            cw, cy = s / h, y + h
            for a in row:
                out.append((x, cy - a / cw, cw, a / cw))
                cy -= a / cw
            x, w = x + cw, w - cw
        else:                                               # a row at the top, filled from the left
            rh, cx = s / w, x
            for a in row:
                out.append((cx, y + h - rh, a / rh, rh))
                cx += a / rh
            h -= rh
    return out


def lines_of(name, width):
    return textwrap.wrap(name, width=width, break_long_words=False) or [name]


def block(lines, size):
    """the text paths of the lines (name lines italic, numbers plain), their width and height at font size `size`"""
    paths = [TextPath((0, 0), t, size=size, prop=NAME if italic else PLAIN) for t, italic in lines]
    width = max(p.get_extents().width for p in paths)
    return paths, width, len(paths) * size * 1.25


def label(ax, x, y, w, h, name, abbr, n, share, big):
    """the best label that fits the rectangle: full name, abbreviation, numbers only, or nothing"""
    nums = [(f"{n:,}", False), (f"{share:.2f}%", False)]
    names = [name] + ([abbr] if isinstance(abbr, str) and abbr and abbr != name else [])
    top = max(6.0, min(22.0 if big else 13.0, math.sqrt(w * h) / 6))
    for candidate in names + [None]:
        size = top
        while size >= 5.5:
            options = [[]] if candidate is None else [lines_of(candidate, k) for k in range(max(8, len(candidate)), 7, -4)]
            for name_lines in options:
                lines = [(t, True) for t in name_lines] + nums
                paths, bw, bh = block(lines, size)
                if bw <= w - 6 and bh <= h - 4:
                    cy = y + h / 2 + bh / 2
                    for p, (t, italic) in zip(paths, lines):
                        cy -= size * 1.25
                        e = p.get_extents()
                        ax.add_patch(PathPatch(p.transformed(Affine2D().translate(x + w / 2 - e.width / 2 - e.x0, cy + size * 0.3)),
                                               facecolor="#222222", edgecolor="none", lw=0))
                    return
            size -= 0.5


pub, src = read("Publishers.csv"), read("Publishers_sources.csv")
pub = pub[pub["Publisher"] != "Unknown publisher"].head(max(1, args.publishers))
k = len(pub)
cols = 1 if k == 1 else (2 if k <= 4 else 3)
rows = math.ceil(k / cols)
fig, axes = plt.subplots(rows, cols, figsize=(cols * 6.6, rows * 5.0), squeeze=False)
for i, (ax, p) in enumerate(zip(axes.flat, pub.itertuples(index=False))):
    s = src[src["Publisher"] == p.Publisher].sort_values("Documents", ascending=False, kind="stable")
    loose = int(s.loc[s["Source title"] == "(no source title)", "Documents"].sum())    # papers without a Source title (books, ...) are not a source: not drawn
    s = s[s["Source title"] != "(no source title)"]
    keep, rest = s.head(max(1, args.tiles)), s.iloc[max(1, args.tiles):]
    tiles = [(r["Source title"], r["Abbreviation"], int(r["Documents"])) for _, r in keep.iterrows()]
    if len(rest):
        tiles.append((f"Other sources ({len(rest)})", None, int(rest["Documents"].sum())))
    top = tiles[0][0]                                               # the largest source gets the panel's colour
    tiles = sorted(tiles, key=lambda t: -t[2])                      # squarify needs sizes from large to small (the group of other sources too)
    total = sum(t[2] for t in tiles)
    for j, ((name, abbr, n), (x, y, w, h)) in enumerate(zip(tiles, squarify([t[2] for t in tiles], 0, 0, W, H))):
        share = 100 * n / total
        other = name.startswith("Other sources (")
        first = name == top
        colour = PANEL[i % len(PANEL)] if first else OTHER if other else BIG if share >= 10 else MID if n >= 2 else ONE
        if not first and colour == PANEL[i % len(PANEL)]:          # never the panel's own colour twice
            colour = "#B9D97A" if colour == BIG else MID
        ax.add_patch(Rectangle((x, y), w, h, facecolor=colour, edgecolor="white", lw=2))
        label(ax, x, y, w, h, str(name), abbr, n, share, first)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    ax.axis("off")
    note = f"\n({loose:,} {'document' if loose == 1 else 'documents'} without a source title not drawn)" if loose else ""
    ax.set_title(f"({chr(97 + i)}) {p.Publisher}: {total:,} documents in {len(s)} sources{note}", fontsize=12, fontfamily="DejaVu Serif")
for ax in list(axes.flat)[k:]:
    ax.axis("off")
fig.suptitle("Sources of the publishers with the most documents (area = documents; % = share of the publisher)", fontweight="bold", fontsize=14)
fig.tight_layout(rect=(0, 0, 1, 0.97))
for ext in ("png", "svg"):
    fig.savefig(HERE / f"publisher_treemaps.{ext}", dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"{k} publishers drawn: " + ", ".join(f"{p} ({n:,})" for p, n in zip(pub["Publisher"], pub["Documents"])))
print("written publisher_treemaps.png and publisher_treemaps.svg")
