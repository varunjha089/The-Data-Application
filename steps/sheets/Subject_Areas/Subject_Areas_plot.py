"""Plot of the sheet "Subject_Areas": documents by Scopus subject area, as a pie chart (the style of Scopus's "Documents by subject area") and as a bar chart
Input : Subject_Areas.csv in this folder (run Subject_Areas.py first)        Output: subject_areas_pie and subject_areas_bar (.png and .svg, same folder)
Pie: the --top areas with most papers, the rest together as "Other"; the percentages are shares of all (paper, subject area) pairs, as in Scopus, so they
     add up to 100. Bar: the same areas, with the number of papers and the share of matched papers (a paper can be in several areas, so these add up to more
     than 100). Papers whose source is not in the Source List are left out of both and named under the title.
Run   : python3 Subject_Areas_plot.py [--top 10]   (needs matplotlib, pandas)
"""
import argparse
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
COLORS = ["#1F77B4", "#D62728", "#2CA02C", "#9467BD", "#FF7F0E", "#17BECF", "#8C564B", "#BCBD22", "#E377C2", "#4C78A8", "#59A14F", "#F28E2B"]
OTHER = "#AAB7B8"

ap = argparse.ArgumentParser(description="Plot of the sheet Subject_Areas")
ap.add_argument("--top", type=int, default=10, help="number of subject areas with their own slice and bar (default 10)")
args = ap.parse_args()


def read(name):
    return pd.read_csv(HERE / name, encoding="utf-8-sig", keep_default_na=False, na_values=[""])


def save(fig, out):
    for ext in ("png", "svg"):
        fig.savefig(HERE / f"{out}.{ext}", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"written {out}.png and {out}.svg")


t = read("Subject_Areas.csv")
areas = t[t["ASJC"].notna()].reset_index(drop=True)                 # the "Not matched" row has no ASJC code
missing = int(t.loc[t["ASJC"].isna(), "Papers"].sum())
top = max(1, args.top)
shown = areas.head(top).copy()
rest = areas.iloc[top:]
note = f"{missing:,} papers whose source is not in the Scopus Source List are left out" if missing else "every paper's source was found in the Scopus Source List"

# ---- pie: labels outside the circle, on leader lines, pushed apart so that they never overlap
pie = shown[["Subject Area", "Papers"]].copy()
if len(rest):
    pie = pd.concat([pie, pd.DataFrame([{"Subject Area": "Other", "Papers": int(rest["Papers"].sum())}])], ignore_index=True)
share = pie["Papers"] / areas["Papers"].sum() * 100
colors = [OTHER if a == "Other" else COLORS[i % len(COLORS)] for i, a in enumerate(pie["Subject Area"])]
fig, ax = plt.subplots(figsize=(10, 7))
wedges, _ = ax.pie(pie["Papers"], colors=colors, startangle=90, counterclock=False, wedgeprops={"linewidth": 1, "edgecolor": "white"})
labels = []
for w, a, s in zip(wedges, pie["Subject Area"], share):
    ang = np.deg2rad((w.theta1 + w.theta2) / 2)
    x, y = np.cos(ang), np.sin(ang)
    labels.append({"x": x, "y": y, "side": 1 if x >= 0 else -1, "ty": 1.25 * y, "text": f"{textwrap.shorten(a, 34, placeholder='…')} ({s:.1f}%)"})
GAP = 0.11                                                          # the smallest distance between two labels on one side (axis units)
for side in (1, -1):
    group = sorted([l for l in labels if l["side"] == side], key=lambda l: l["ty"])
    for i in range(1, len(group)):                                  # push labels up until each is GAP above the one below it
        group[i]["ty"] = max(group[i]["ty"], group[i - 1]["ty"] + GAP)
    over = (group[-1]["ty"] - 1.3) if group else 0
    if over > 0:                                                    # the top label went too high: shift the whole side down and push down again
        for l in group:
            l["ty"] -= over
        for i in range(len(group) - 2, -1, -1):
            group[i]["ty"] = min(group[i]["ty"], group[i + 1]["ty"] - GAP)
for l in labels:
    tx = 1.32 * l["side"]
    ax.annotate(l["text"], xy=(l["x"], l["y"]), xytext=(tx, l["ty"]), ha="left" if l["side"] > 0 else "right", va="center", fontsize=10,
                arrowprops={"arrowstyle": "-", "color": "#7F7F7F", "lw": 0.8, "connectionstyle": "arc,angleA=180,angleB=0,armA=0,armB=20,rad=0" if l["side"] > 0
                            else "arc,angleA=0,angleB=0,armA=0,armB=20,rad=0", "shrinkA": 0, "shrinkB": 0})
ax.set_title(f"Documents by subject area (N={int(areas['Papers'].sum()):,} paper–area pairs)", fontweight="bold", pad=28)
ax.text(0.5, 1.01, note, transform=ax.transAxes, ha="center", fontsize=9, color="#555555")
ax.set_aspect("equal")
save(fig, "subject_areas_pie")

# ---- bar: number of papers per area, largest at the top
fig, ax = plt.subplots(figsize=(9, 0.45 * len(shown) + 1.6))
y = np.arange(len(shown))[::-1]
ax.barh(y, shown["Papers"], color=[COLORS[i % len(COLORS)] for i in range(len(shown))], height=0.7)
ax.set_yticks(y, shown["Subject Area"])
for yi, n, pct in zip(y, shown["Papers"], shown["Share of Matched Papers (%)"]):
    ax.text(n, yi, f"  {int(n):,} ({pct:.1f}%)", va="center", fontsize=9)
ax.set_xlabel("Papers (a paper counts in every subject area of its source)")
ax.set_xlim(0, shown["Papers"].max() * 1.22)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
more = f"; {len(rest)} more areas in the table" if len(rest) else ""
ax.set_title(f"Papers by subject area (top {len(shown)}; % of the matched papers{more})", fontweight="bold")
ax.text(0, -0.13 if len(shown) > 6 else -0.25, note, transform=ax.transAxes, fontsize=9, color="#555555")
save(fig, "subject_areas_bar")
