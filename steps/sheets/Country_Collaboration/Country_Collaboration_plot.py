"""Plots of the sheet "Country_Collaboration": the 15 pairs of countries with the most joint papers, and the chord diagram of the six most productive countries and the rest of the world
Input : Country_Collaboration.csv and Country_Collaboration_chord.csv in this folder (run Country_Collaboration.py first)        Output: top_country_pairs and chord_diagram (.png and .svg, same folder)
Run   : python3 Country_Collaboration_plot.py   (needs matplotlib)
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


def read(name="Country_Collaboration.csv"):
    return pd.read_csv(HERE / name, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype={"Author ID": str})


def short(text, n=48):
    text = str(text)
    return text if len(text) <= n else text[: n - 1] + "..."


def save(fig, name):
    fig.savefig(HERE / f"{name}.png", dpi=150, bbox_inches="tight")
    fig.savefig(HERE / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)
    print(f"written {name}.png and {name}.svg")


t = read().head(15).iloc[::-1]
fig, ax = plt.subplots(figsize=(9, 0.45 * len(t) + 1.8))
ax.barh([f"{a} - {b}" for a, b in zip(t["from_country"], t["to_country"])], t["papers"], color=PURPLE)
for i, v in enumerate(t["papers"]):
    ax.text(v + t["papers"].max() * 0.01, i, str(v), va="center")
ax.set_xlabel("Joint papers")
ax.set_xlim(0, t["papers"].max() * 1.1)
ax.set_title("Country collaboration: pairs with most joint papers")
save(fig, "top_country_pairs")


# 2. chord diagram
import numpy as np
from matplotlib.patches import PathPatch, Wedge
from matplotlib.path import Path

e = read("Country_Collaboration_chord.csv")
REST = "Rest of the World"
rest_rest = int(e.loc[(e["from_node"] == REST) & (e["to_node"] == REST), "links"].sum())
e = e[e["from_node"] != e["to_node"]]                       # a link inside the Rest of the World is not drawn
tot = {}
for r in e.itertuples():
    tot[r.from_node] = tot.get(r.from_node, 0) + r.links
    tot[r.to_node] = tot.get(r.to_node, 0) + r.links
nodes = sorted(tot, key=lambda n: -tot[n])
palette = ["#4C78A8", "#F58518", "#54A24B", "#E45756", "#B279A2", "#72B7B2", "#9D755D"]
col = {n: palette[i % len(palette)] for i, n in enumerate(nodes)}
gap = 0.04
scale = (2 * np.pi - gap * len(nodes)) / sum(tot.values())
start, ang = {}, np.pi / 2
for n in nodes:
    start[n] = ang
    ang -= tot[n] * scale + gap
mid = {n: start[n] - tot[n] * scale / 2 for n in nodes}
slot = {}                                                   # (node, partner) -> (angle high, angle low); partners ordered to reduce crossings
for n in nodes:
    ps = [(r.to_node if r.from_node == n else r.from_node, r.links) for r in e.itertuples() if n in (r.from_node, r.to_node)]
    ps.sort(key=lambda x: (mid[x[0]] - mid[n]) % (2 * np.pi))
    t = start[n]
    for q, links in ps:
        slot[(n, q)] = (t, t - links * scale)
        t -= links * scale
fig, ax = plt.subplots(figsize=(9, 9))
ax.set_aspect("equal")
ax.axis("off")
R, w = 1.0, 0.07
pt = lambda a, r=R - w: np.array([r * np.cos(a), r * np.sin(a)])
for n in nodes:
    t1 = start[n]
    t0 = t1 - tot[n] * scale
    ax.add_patch(Wedge((0, 0), R, np.degrees(t0), np.degrees(t1), width=w, color=col[n], lw=0))
    tm = (t0 + t1) / 2
    p = pt(tm, R + 0.07)
    ax.text(p[0], p[1], f"{n} ({tot[n]})", ha="left" if np.cos(tm) >= 0 else "right", va="center", fontsize=11)
for r in e.sort_values("links", ascending=False).itertuples():
    a1, a0 = slot[(r.from_node, r.to_node)]
    b1, b0 = slot[(r.to_node, r.from_node)]
    arc = lambda s, f: [pt(a) for a in np.linspace(s, f, 12)]
    pa, pb = arc(a1, a0), arc(b1, b0)
    verts, codes = [pa[0]], [Path.MOVETO]
    for q in pa[1:]:
        verts.append(q); codes.append(Path.LINETO)
    verts += [(0, 0), pb[0]]; codes += [Path.CURVE3, Path.CURVE3]
    for q in pb[1:]:
        verts.append(q); codes.append(Path.LINETO)
    verts += [(0, 0), pa[0]]; codes += [Path.CURVE3, Path.CURVE3]
    ax.add_patch(PathPatch(Path(verts, codes), fc=col[r.from_node], ec="white", lw=0.4, alpha=0.62))
ax.set_xlim(-1.6, 1.6)
ax.set_ylim(-1.25, 1.25)
ax.set_title("Country collaboration: the six most productive countries and the rest of the world", fontsize=12)
fig.text(0.5, 0.1, f"A link is a pair of countries on the same paper. The {rest_rest} links between two 'Rest of the World' countries are not drawn.\nThe number after each name is the number of links drawn at that country.",
         ha="center", fontsize=9, color="#555")
save(fig, "chord_diagram")
