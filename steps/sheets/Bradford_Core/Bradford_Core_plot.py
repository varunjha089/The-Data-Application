"""Plot of the sheet "Bradford_Core": which countries, authors and institutions publish most in the Bradford core sources, and how well those papers are cited.
Input : Bradford_Core.csv, Bradford_Core_matrix.csv, Bradford_Core_baseline.csv in this folder (run Bradford_Core.py first)
Output: for each kind (countries, authors, institutions), three pictures (.png and .svg, same folder):
        core_<kind>_pyramid     population pyramid: papers in the core sources (left, blue) and in other sources (right, grey), with the share in the core
        core_<kind>_heatmap     papers of each actor in each core source (numbered as in the Bradford plot)
        core_<kind>_cpp         citations per paper outside the core against inside it (only actors with at least 3 papers on each side)
        core_<kind>_ncs         the same corrected for age: normalised citation score (1 = cited like the average paper of the same year), core against outside
Run   : python3 Bradford_Core_plot.py [--only core_countries|core_authors|core_institutions]   (needs matplotlib, pandas)
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

HERE = Path(__file__).resolve().parent
BLUE, ORANGE, GREY = "#2F6DB5", "#F28E2B", "#C9CDD2"
plt.rcParams.update({"font.size": 11, "axes.titlesize": 14, "axes.titleweight": "bold", "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "#E3E3E3", "axes.axisbelow": True})
KINDS = {"core_countries": ("Countries", "countries", "country"), "core_authors": ("Authors", "authors", "author"), "core_institutions": ("Institutions", "institutions", "institution")}
MIN_SIDE = 3          # an actor needs this many papers inside and outside the core to be compared on citations


def short(text, n=48):
    text = str(text)
    return text if len(text) <= n else text[: n - 1] + "..."


def save(fig, name):
    fig.savefig(HERE / f"{name}.png", dpi=150, bbox_inches="tight")
    fig.savefig(HERE / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)
    print(f"written {name}.png and {name}.svg")


T = pd.read_csv(HERE / "Bradford_Core.csv", encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype={"Entity": str})
M = pd.read_csv(HERE / "Bradford_Core_matrix.csv", encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype={"Entity": str})
B = pd.read_csv(HERE / "Bradford_Core_baseline.csv", encoding="utf-8-sig").set_index("Kind")
TOP = M.groupby("Kind")["Entity"].nunique().max()           # the sheet's --top: the matrix holds exactly that many actors per kind


def pyramid(kind, noun):
    """population pyramid: papers in the core sources to the left, papers in other sources to the right, one shared axis (the counts differ a lot between actors)"""
    t = T[T["Kind"] == kind].head(TOP).iloc[::-1]
    names = [short(n, 40) for n in t["Name"]]
    core, other = t["Core_Papers"].to_numpy(), (t["Papers"] - t["Core_Papers"]).to_numpy()
    m = max(core.max(), other.max())
    fig, ax = plt.subplots(figsize=(10.5, 0.42 * len(t) + 2.1))
    ax.barh(names, -core, color=BLUE, label="Papers in the core sources")
    ax.barh(names, other, color=GREY, label="Papers in other sources")
    for i, (c, o) in enumerate(zip(core, other)):
        ax.text(-c - m * 0.01, i, f"{c}", ha="right", va="center", fontsize=9)
        ax.text(o + m * 0.01, i, f"{o}", ha="left", va="center", fontsize=9)
    ax.axvline(0, color="#333", lw=0.8)
    ax.set_xlim(-m * 1.12, m * 1.12)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{abs(v):g}"))          # both sides count papers: no minus sign
    ax.set_xlabel("Papers")
    ax.grid(axis="y", visible=False)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.text(1.02, len(t) - 0.35, "In the core", transform=ax.get_yaxis_transform(), ha="left", va="bottom", fontsize=9, fontweight="bold")
    for i, sh in enumerate(t["Core_Share_pct"]):
        ax.text(1.02, i, f"{sh:.0f}%", transform=ax.get_yaxis_transform(), ha="left", va="center", fontsize=9)
    ax.legend(loc="lower right", frameon=False)
    share = B.loc[kind, "Core share %"]
    ax.set_title(f"The {len(t)} {noun} with most papers in the Bradford core sources\n(for all {kind.lower()} together {share:.0f}% of the papers are in the core)", fontsize=12)
    return fig


def heat(kind, noun):
    m = M[M["Kind"] == kind]
    cols = sorted(int(c) for c in m["Core source no."].unique())
    src = dict(zip(m["Core source no."].astype(int), m["Source"]))
    order = T[T["Kind"] == kind].head(TOP)["Name"].tolist()
    p = m.astype({"Core source no.": int}).pivot_table(index="Name", columns="Core source no.", values="Papers", aggfunc="sum").reindex(index=order, columns=cols).fillna(0)
    fig, ax = plt.subplots(figsize=(0.62 * len(cols) + 4.2, 0.42 * len(p) + 3.6))
    ax.imshow(p.to_numpy(), cmap="Blues", aspect="auto")
    ax.set_xticks(range(len(cols)), [f"{c}. {short(src[c], 30)}" for c in cols], rotation=50, ha="right", fontsize=9)
    ax.set_yticks(range(len(p)), [short(n, 38) for n in p.index])
    ax.grid(False)
    mx = p.to_numpy().max()
    for i in range(p.shape[0]):
        for j in range(p.shape[1]):
            v = int(p.iat[i, j])
            if v:
                ax.text(j, i, v, ha="center", va="center", fontsize=9, color="white" if v > mx * 0.55 else "black")
    ax.set_title(f"Papers of the top {len(p)} {noun} in each core source\n(sources numbered as in the Bradford plot)", fontsize=12)
    return fig


def cpp(kind, noun):
    t = T[(T["Kind"] == kind) & (T["Core_Papers"] >= MIN_SIDE) & (T["Papers"] - T["Core_Papers"] >= MIN_SIDE)].head(TOP).iloc[::-1]
    if t.empty:
        print(f"{kind}: no actor has {MIN_SIDE} papers on each side; citation picture skipped")
        return None
    fig, ax = plt.subplots(figsize=(10, 0.42 * len(t) + 2.1))
    y = range(len(t))
    ax.hlines(y, t["CPP_outside"], t["CPP_core"], color="#B9BEC4", lw=2, zorder=1)
    ax.scatter(t["CPP_outside"], y, s=70, color=GREY, edgecolor="#6B7078", zorder=2, label="Citations per paper, papers in other sources")
    ax.scatter(t["CPP_core"], y, s=70, color=BLUE, edgecolor="white", zorder=3, label="Citations per paper, papers in the core sources")
    ax.set_yticks(list(y), [short(n, 40) for n in t["Name"]])
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Citations per paper (not corrected for age)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=1, frameon=False, fontsize=10)
    b = B.loc[kind]
    ax.set_title(f"Are the core papers cited more? ({len(t)} {noun} with at least {MIN_SIDE} papers on each side)\nWhole corpus: {b['CPP core']:.1f} citations per paper in the core, {b['CPP outside']:.1f} outside", fontsize=12)
    return fig


def ncs(kind, noun):
    """citations corrected for age: the actor's papers against the average paper of the same year (1), core papers against the others"""
    t = T[(T["Kind"] == kind) & (T["Core_Papers"] >= MIN_SIDE) & (T["Papers"] - T["Core_Papers"] >= MIN_SIDE)].head(TOP).iloc[::-1]
    if "NCS_core" not in T.columns or t.empty:
        print(f"{kind}: no actor has {MIN_SIDE} papers on each side (or the data has no NCS columns); age-corrected picture skipped")
        return None
    fig, ax = plt.subplots(figsize=(10, 0.42 * len(t) + 2.3))
    y = range(len(t))
    ax.axvline(1, color="#555555", lw=1, ls="--", zorder=0)
    ax.text(1, len(t) - 0.4, " average paper of the same year", fontsize=9, color="#555555", va="bottom")
    ax.hlines(y, t["NCS_outside"], t["NCS_core"], color="#B9BEC4", lw=2, zorder=1)
    ax.scatter(t["NCS_outside"], y, s=70, color=GREY, edgecolor="#6B7078", zorder=2, label="Papers in other sources")
    ax.scatter(t["NCS_core"], y, s=70, color=BLUE, edgecolor="white", zorder=3, label="Papers in the core sources")
    ax.set_yticks(list(y), [short(n, 40) for n in t["Name"]])
    ax.set_ylim(-0.7, len(t) + 0.3)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Normalised citation score (citations / mean citations of the papers of the same year)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2, frameon=False, fontsize=10)
    b = B.loc[kind]
    extra = f"\nWhole corpus: {b['NCS core']:.2f} in the core, {b['NCS outside']:.2f} outside" if "NCS core" in B.columns else ""
    ax.set_title(f"Are the core papers cited more, for their age? ({len(t)} {noun}){extra}", fontsize=12)
    return fig


ap = argparse.ArgumentParser()
ap.add_argument("--only", choices=sorted(KINDS), help="make only the pictures of this kind")
a = ap.parse_args()
for pid, (kind, tag, noun) in KINDS.items():
    if a.only in (None, pid):
        for name, fn in (("pyramid", pyramid), ("heatmap", heat), ("cpp", cpp), ("ncs", ncs)):
            fig = fn(kind, tag)
            if fig is not None:
                save(fig, f"core_{tag}_{name}")
