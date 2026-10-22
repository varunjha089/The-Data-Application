"""Plots of the sheet "10_Source_Impact": the impact of the sources seen in several ways, so the user can choose the one that tells the story best.
Input : 10_Source_Impact.csv in this folder (run 10_Source_Impact.py first)
Output (.png and .svg, same folder), one file per plot; "python3 10_Source_Impact_plot.py --only ID" makes one, without --only all are made:
  source_h_index                 bars: the sources with the highest h-index (with papers and citations written next to the bar)
  source_pyramid_papers_vs_cpp   pyramid: papers (left) and citations per paper (right)
  source_pyramid_h_vs_g          pyramid: h-index (left) and g-index (right)
  source_bubble                  bubbles: papers (x) against citations (y), size = h-index, colour = first year; the top sources are named
  source_dumbbell_h_g            dumbbell: h-index and g-index of every source joined by a line (the gap = dependence on a few star papers)
  source_heatmap                 heat map: the profile of every source (h, g, m, papers, citations; every column scaled 0 to 1, the real value written in the cell)
  source_cpp_bars                bars: citations per paper (takes the size of the source out)
  source_m_vs_year               scatter: m-index (h-index / years since the first paper) against the first year
The sources "in the plots" are the top n chosen in the application (column "In plots" of the CSV; default 15).
Run   : python3 10_Source_Impact_plot.py [--only ID]   (needs matplotlib, pandas, numpy)
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
BLUE, ORANGE, GREEN, RED, PURPLE, GREY = "#2F6DB5", "#F28E2B", "#59A14F", "#D6504A", "#9B6BB5", "#9AA0A6"
LEFT, RIGHT = "#4C78A8", "#F58518"
plt.rcParams.update({"font.size": 11, "axes.titlesize": 14, "axes.titleweight": "bold", "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "#E3E3E3", "axes.axisbelow": True})


def read(name="10_Source_Impact.csv"):
    return pd.read_csv(HERE / name, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype={"Author ID": str})


def short(text, n=48):
    text = str(text)
    return text if len(text) <= n else text[: n - 1] + "..."


def save(fig, name):
    fig.savefig(HERE / f"{name}.png", dpi=150, bbox_inches="tight")
    fig.savefig(HERE / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)
    print(f"written {name}.png and {name}.svg")


ALL = read()
ALL["CPP"] = (ALL["TC"] / ALL["NP"]).round(1)                          # citations per paper
TOP = ALL[ALL["In plots"] == 1].sort_values(["h_index", "TC", "Source title"], ascending=[False, False, True], kind="stable") if "In plots" in ALL else \
    ALL.sort_values(["h_index", "TC"], ascending=False).head(15)
N = len(TOP)
PLOTS = {}


OFFSETS = [(6, 6, "left"), (6, -13, "left"), (-6, 6, "right"), (-6, -13, "right")]     # labels of crowded points take turns in four directions


def label_points(ax, t, xcol, ycol, k=8, floor=None, offsets=OFFSETS):
    for i, (_, r) in enumerate(t.head(k).iterrows()):
        dx, dy, ha = offsets[i % len(offsets)]
        y = r[ycol] if floor is None else max(r[ycol], floor)
        ax.annotate(short(r["Source title"], 26), (r[xcol], y), xytext=(dx, dy), textcoords="offset points", ha=ha, fontsize=8.5)


def plot(fn):
    PLOTS[fn.__name__] = fn
    return fn


def pyramid(t, left, right, lname, rname, title, name, fmt_r="{:g}"):
    t = t.iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 0.45 * len(t) + 1.9))
    labels = [short(s, 45) for s in t["Source title"]]
    lv, rv = t[left].to_numpy(float), t[right].to_numpy(float)
    ax.barh(labels, -lv / lv.max(), color=LEFT, label=lname)               # each side has its own scale (the bar = value / largest value of that side)
    ax.barh(labels, rv / rv.max(), color=RIGHT, label=rname)
    for i, (a, b) in enumerate(zip(lv, rv)):
        ax.text(-a / lv.max() - 0.01, i, f"{a:g}", ha="right", va="center", fontsize=9)
        ax.text(b / rv.max() + 0.01, i, fmt_r.format(b), va="center", fontsize=9)
    ax.axvline(0, color="#333", lw=0.8)
    ax.set_xlim(-1.18, 1.18)
    ax.set_xticks([])
    ax.grid(False)
    ax.spines[["top", "right", "bottom"]].set_visible(False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=2, frameon=False)
    ax.set_title(title, fontsize=12)
    ax.text(0.5, -0.09, "Each side has its own scale (bar = value / largest value of that side).", transform=ax.transAxes, ha="center", fontsize=9, color="#555")
    save(fig, name)


@plot
def source_h_index():
    t = TOP.iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 0.5 * len(t) + 1.8))
    ax.barh([short(s, 60) for s in t["Source title"]], t["h_index"], color=GREEN)
    for i, (h, np_, tc) in enumerate(zip(t["h_index"], t["NP"], t["TC"])):
        ax.text(h + 0.3, i, f"h = {h}   ({np_} papers, {tc} citations)", va="center", fontsize=10)
    ax.set_xlabel("h-index of the source")
    ax.set_xlim(0, t["h_index"].max() * 1.5)
    ax.set_title("Sources' local impact (h-index)")
    save(fig, "source_h_index")


@plot
def source_pyramid_papers_vs_cpp():
    t = TOP.sort_values(["NP", "TC"], ascending=False)
    pyramid(t, "NP", "CPP", "Papers", "Citations per paper", f"Top {N} sources: papers (left) and citations per paper (right)", "source_pyramid_papers_vs_cpp", "{:.1f}")


@plot
def source_pyramid_h_vs_g():
    pyramid(TOP, "h_index", "g_index", "h-index", "g-index", f"Top {N} sources: h-index (left) and g-index (right)", "source_pyramid_h_vs_g")


@plot
def source_bubble():
    fig, ax = plt.subplots(figsize=(10, 6.6))
    sc = ax.scatter(ALL["NP"], ALL["TC"].clip(lower=0.5), s=30 + 40 * ALL["h_index"], c=ALL["PY_start"], cmap="viridis", alpha=0.65, edgecolor="white", linewidth=0.5)
    ax.set_xscale("log")
    ax.set_yscale("log")
    label_points(ax, TOP, "NP", "TC", 8, 0.5)                              # the 8 sources with the highest h-index are named
    ax.set_xlim(right=ALL["NP"].max() * 2.2)
    ax.set_xlabel("Papers (log scale)")
    ax.set_ylabel("Citations (log scale)")
    ax.set_title("Papers and citations of the sources (bubble size = h-index)")
    cb = fig.colorbar(sc, ax=ax, pad=0.02)
    cb.set_label("First year of the source in the data")
    save(fig, "source_bubble")


@plot
def source_dumbbell_h_g():
    t = TOP.iloc[::-1]
    y = np.arange(len(t))
    fig, ax = plt.subplots(figsize=(10, 0.5 * len(t) + 1.8))
    ax.hlines(y, t["h_index"], t["g_index"], color="#B8B8B8", lw=3, zorder=1)
    ax.scatter(t["h_index"], y, color=BLUE, s=70, zorder=2, label="h-index")
    ax.scatter(t["g_index"], y, color=ORANGE, s=70, zorder=2, label="g-index")
    ax.set_yticks(y, [short(s, 55) for s in t["Source title"]])
    ax.set_xlabel("Index value")
    ax.legend(frameon=False, loc="lower right")
    ax.set_title("h-index and g-index of the sources (a long line = a few very highly cited papers)")
    save(fig, "source_dumbbell_h_g")


@plot
def source_heatmap():
    cols = [("h_index", "h"), ("g_index", "g"), ("m_index", "m"), ("NP", "Papers"), ("TC", "Citations")]
    m = TOP[[c for c, _ in cols]].to_numpy(float)
    scaled = m / m.max(axis=0)
    fig, ax = plt.subplots(figsize=(8.5, 0.5 * len(TOP) + 2.2))
    ax.imshow(scaled, cmap="Blues", aspect="auto", vmin=0, vmax=1)
    ax.set_xticks(range(len(cols)), [n for _, n in cols])
    ax.set_yticks(range(len(TOP)), [short(s, 45) for s in TOP["Source title"]])
    ax.xaxis.tick_top()
    ax.grid(False)
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            ax.text(j, i, f"{m[i, j]:g}", ha="center", va="center", fontsize=9, color="white" if scaled[i, j] > 0.55 else "black")
    ax.set_title("Profile of the top sources (every column scaled to its own maximum)", pad=28)
    save(fig, "source_heatmap")


@plot
def source_cpp_bars():
    t = TOP.sort_values("CPP", ascending=True)
    fig, ax = plt.subplots(figsize=(10, 0.5 * len(t) + 1.8))
    ax.barh([short(s, 60) for s in t["Source title"]], t["CPP"], color=PURPLE)
    for i, (c, n) in enumerate(zip(t["CPP"], t["NP"])):
        ax.text(c + t["CPP"].max() * 0.01, i, f"{c:g}  ({n} papers)", va="center", fontsize=10)
    ax.set_xlabel("Citations per paper")
    ax.set_xlim(0, t["CPP"].max() * 1.3)
    ax.set_title(f"Citations per paper of the top {N} sources")
    save(fig, "source_cpp_bars")


@plot
def source_m_vs_year():
    fig, ax = plt.subplots(figsize=(10, 6.2))
    ax.scatter(ALL["PY_start"] + np.random.default_rng(1).uniform(-0.18, 0.18, len(ALL)), ALL["m_index"], s=28, color=BLUE, alpha=0.4, edgecolor="none")
    ax.scatter(TOP["PY_start"], TOP["m_index"], s=60, color=ORANGE, edgecolor="white", zorder=3)
    label_points(ax, TOP.sort_values("m_index", ascending=False), "PY_start", "m_index", 8, offsets=OFFSETS[:2])       # the 8 sources with the highest m-index are named
    ax.set_xticks(range(int(ALL["PY_start"].min()), int(ALL["PY_start"].max()) + 1))
    ax.set_xlabel("First year of the source in the data")
    ax.set_ylabel("m-index (h-index / years since the first paper)")
    ax.set_title("m-index against first year (orange = the top sources)")
    save(fig, "source_m_vs_year")


ap = argparse.ArgumentParser()
ap.add_argument("--only", choices=sorted(PLOTS), help="make only this plot")
a = ap.parse_args()
for name, fn in PLOTS.items():
    if a.only in (None, name):
        fn()
