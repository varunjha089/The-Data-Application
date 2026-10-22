"""Plot of the sheet "World_Map": world map of the 15 most productive countries (name and number of documents on the map)
Input : World_Map.csv in this folder (run World_Map.py first)        Output: world_map_top15 (.png and .svg, same folder)
Run   : python3 World_Map_plot.py   (needs matplotlib)
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
BLUE, ORANGE, GREEN, RED, PURPLE, GREY = "#2F6DB5", "#F28E2B", "#59A14F", "#D6504A", "#9B6BB5", "#9AA0A6"
plt.rcParams.update({"font.size": 11, "axes.titlesize": 14, "axes.titleweight": "bold", "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "#E3E3E3", "axes.axisbelow": True})


def read(name="World_Map.csv"):
    return pd.read_csv(HERE / name, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype={"Author ID": str})


def short(text, n=48):
    text = str(text)
    return text if len(text) <= n else text[: n - 1] + "..."


def save(fig, name):
    fig.savefig(HERE / f"{name}.png", dpi=150, bbox_inches="tight")
    fig.savefig(HERE / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)
    print(f"written {name}.png and {name}.svg")


import json
import numpy as np
from matplotlib.patches import Polygon, Rectangle

t = read()
t = t[t["In map"] == 1]                  # the countries chosen in the application (World_Map.py --top-countries, default 15)
TOP = len(t)
# country polygons: Natural Earth 10 m, 'India' worldview (the boundaries of India as in the official map of India), simplified; file next to this script
geoms = {}
for name, rings in json.load(open(HERE / "world_countries_india_view.json")).items():
    out = []
    for ring in rings:
        xs = [p[0] for p in ring]
        out.append([(x + 360 if (max(xs) - min(xs) > 180 and x < 0) else x, y) for x, y in ring])     # a ring that crosses the date line
    geoms[name] = out
NAME = {"Russian Federation": "Russia", "Czech Republic": "Czechia", "Democratic Republic Congo": "Democratic Republic of the Congo",
        "South Korea": "Republic of Korea", "Cote d'Ivoire": "Côte d'Ivoire", "Dominican Republic": "Dominican Rep."}
nm = lambda c: NAME.get(c, c)


def centroid(name):
    ring = max(geoms[name], key=lambda r: abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(r, r[1:]))))
    a = np.array(ring)
    x0, y0, x1, y1 = a[:, 0], a[:, 1], np.roll(a[:, 0], -1), np.roll(a[:, 1], -1)
    cr = x0 * y1 - x1 * y0
    area = cr.sum() / 2
    return (((x0 + x1) * cr).sum() / (6 * area), ((y0 + y1) * cr).sum() / (6 * area)) if abs(area) > 1e-9 else (a[:, 0].mean(), a[:, 1].mean())


# four colour classes from the values of the 15 countries (quartiles)
v = t["Documents"]
edges = sorted({int(round(q)) for q in np.quantile(v, [0.25, 0.5, 0.75])})
CLASS_COLOURS = ["#9ECAE1", "#4292C6", "#2171B5", "#08306B"][: len(edges) + 1]
bounds = [int(v.min())] + [e + 1 for e in edges] + [int(v.max()) + 1]
def klass(x):
    return sum(x > e for e in edges)
value = {nm(c): int(d) for c, d in zip(t["Country"], t["Documents"])}
colour = lambda name: CLASS_COLOURS[klass(value[name])] if name in value else "#EDEDED"

fig, ax = plt.subplots(figsize=(14, 6.0))
for name, rings in geoms.items():
    if name == "Antarctica":
        continue
    for ring in rings:
        ax.add_patch(Polygon(ring, closed=True, fc=colour(name), ec="white", lw=0.3))
ax.set_xlim(-170, 190)
ax.set_ylim(-56, 88)
ax.set_aspect("equal")
ax.axis("off")
# crowded countries get a box with a leader line, the others are labelled on the country itself
OFF = {"United Kingdom": (-30, 70, "right"), "Netherlands": (-14, 80, "center"), "Germany": (20, 80, "center"), "France": (-26, 38, "right"),
       "Spain": (-26, 27, "right"), "Italy": (12, 20, "center"), "Greece": (34, 21, "center"), "South Korea": (146, 22, "left"), "Egypt": (38, 8, "center"),
       "Belgium": (-12, 70, "center"), "Switzerland": (-2, 26, "center"), "Portugal": (-26, 16, "right"), "Denmark": (6, 84, "center"), "Taiwan": (146, 8, "left")}
for country, n in zip(t["Country"], t["Documents"]):
    name = nm(country)
    if name not in geoms:
        continue
    x, y = centroid(name)
    text = f"{country}\n{int(n)}"
    if name in OFF or country in OFF:
        tx, ty, ha = OFF.get(country, OFF.get(name))
        ax.annotate(text, (x, y), xytext=(tx, ty), fontsize=8.5, ha=ha, va="center", fontweight="bold", zorder=5, bbox=dict(fc="white", ec="#999", lw=0.5, boxstyle="round,pad=0.25"),
                    arrowprops=dict(arrowstyle="-", color="#444", lw=0.7, shrinkA=0, shrinkB=1))
    else:
        ax.text(x, y, text, fontsize=9, ha="center", va="center", fontweight="bold", color="white" if klass(n) >= 2 else "black", zorder=5)
for i, c in enumerate(CLASS_COLOURS):
    lo, hi = bounds[i], bounds[i + 1] - 1
    ax.add_patch(Rectangle((0, 0), 0, 0, fc=c, label=f"{lo}-{hi}" if hi > lo else f"{lo}"))
ax.legend(title="Documents", loc="lower left", frameon=False, fontsize=9, bbox_to_anchor=(0.02, 0.12))
ax.set_title(f"{TOP} Most Productive Countries", fontsize=14)
save(fig, "world_map_top15")
