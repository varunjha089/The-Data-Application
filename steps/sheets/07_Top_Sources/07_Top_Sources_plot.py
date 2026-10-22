"""Plot of the sheet "07_Top_Sources": documents of the most productive sources
Input : 07_Top_Sources.csv in this folder (run 07_Top_Sources.py first)        Output: top_sources (.png and .svg, same folder)
Run   : python3 07_Top_Sources_plot.py   (needs matplotlib)
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


def read(name="07_Top_Sources.csv"):
    return pd.read_csv(HERE / name, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype={"Author ID": str})


def short(text, n=48):
    text = str(text)
    return text if len(text) <= n else text[: n - 1] + "..."


def save(fig, name):
    fig.savefig(HERE / f"{name}.png", dpi=150, bbox_inches="tight")
    fig.savefig(HERE / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)
    print(f"written {name}.png and {name}.svg")


t = read().sort_values("Documents")
fig, ax = plt.subplots(figsize=(10, 0.5 * len(t) + 1.8))
ax.barh([short(s, 60) for s in t["Source title"]], t["Documents"], color=BLUE)
for i, v in enumerate(t["Documents"]):
    ax.text(v + t["Documents"].max() * 0.01, i, str(v), va="center")
ax.set_xlabel("Documents")
ax.set_title("Most relevant sources")
ax.set_xlim(0, t["Documents"].max() * 1.12)
save(fig, "top_sources")
