"""Plot of the sheet "19_Corr_Countries": papers by country of the corresponding author, single-country (SCP) and multi-country (MCP)
Input : 19_Corr_Countries.csv in this folder (run 19_Corr_Countries.py first)        Output: corresponding_countries and pyramid_scp_vs_mcp (.png and .svg, same folder)
Run   : python3 19_Corr_Countries_plot.py   (needs matplotlib)
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


def read(name="19_Corr_Countries.csv"):
    return pd.read_csv(HERE / name, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype={"Author ID": str})


def short(text, n=48):
    text = str(text)
    return text if len(text) <= n else text[: n - 1] + "..."


def save(fig, name):
    fig.savefig(HERE / f"{name}.png", dpi=150, bbox_inches="tight")
    fig.savefig(HERE / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)
    print(f"written {name}.png and {name}.svg")


t = read().sort_values("Grand Total")
fig, ax = plt.subplots(figsize=(10, 0.5 * len(t) + 1.9))
ax.barh(t["Corresponding Country"], t["SCP"], color=ORANGE, label="Single-country papers (SCP)")
ax.barh(t["Corresponding Country"], t["MCP"], left=t["SCP"], color=BLUE, label="Multi-country papers (MCP)")
for i, (s, m) in enumerate(zip(t["SCP"], t["MCP"])):
    ax.text(s + m + t["Grand Total"].max() * 0.01, i, f"{s + m}  (MCP {m / (s + m) * 100:.0f}%)", va="center", fontsize=10)
ax.set_xlabel("Papers")
ax.set_xlim(0, t["Grand Total"].max() * 1.22)
ax.legend(frameon=False, loc="lower right")
ax.set_title("Corresponding author's country")
save(fig, "corresponding_countries")

# second option: the same numbers as a pyramid (single-country papers to the left, multi-country papers to the right of one axis)
p = read().sort_values("Grand Total", ascending=False)
labels, left, right = list(p["Corresponding Country"])[::-1], list(p["SCP"])[::-1], list(p["MCP"])[::-1]
fig, ax = plt.subplots(figsize=(9, 0.45 * len(labels) + 1.8))
ax.barh(labels, [-v for v in left], color="#4C78A8", label="Single-country papers (SCP)")
ax.barh(labels, right, color="#F58518", label="Multi-country papers (MCP)")
m = max(max(left), max(right))
for i, (a, b) in enumerate(zip(left, right)):
    ax.text(-a - m * 0.01, i, f"{a:g}", ha="right", va="center", fontsize=9)
    ax.text(b + m * 0.01, i, f"{b:g}", va="center", fontsize=9)
ax.axvline(0, color="#333", lw=0.8)
ax.set_xlim(-m * 1.18, m * 1.18)
ax.set_xticks([])
ax.grid(False)
ax.spines[["top", "right", "bottom"]].set_visible(False)
ax.legend(loc="lower right", frameon=False)
ax.set_title("Single- vs multi-country papers (corresponding author's country)", fontsize=12)
save(fig, "pyramid_scp_vs_mcp")
