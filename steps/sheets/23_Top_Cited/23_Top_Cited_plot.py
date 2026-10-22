"""Plot of the sheet "23_Top_Cited": citations of the 20 most cited documents
Input : 23_Top_Cited.csv in this folder (run 23_Top_Cited.py first)        Output: top_cited (.png and .svg, same folder)
Run   : python3 23_Top_Cited_plot.py   (needs matplotlib)
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


def read(name="23_Top_Cited.csv"):
    return pd.read_csv(HERE / name, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype={"Author ID": str})


def short(text, n=48):
    text = str(text)
    return text if len(text) <= n else text[: n - 1] + "..."


def save(fig, name):
    fig.savefig(HERE / f"{name}.png", dpi=150, bbox_inches="tight")
    fig.savefig(HERE / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)
    print(f"written {name}.png and {name}.svg")


t = read().iloc[::-1]
fig, ax = plt.subplots(figsize=(11, 0.42 * len(t) + 1.8))
ax.barh([f"{short(ti, 62)} ({y})" for ti, y in zip(t["Title"], t["Year"])], t["Cited by"], color=RED)
for i, (c, per) in enumerate(zip(t["Cited by"], t["TC per Year"])):
    ax.text(c + t["Cited by"].max() * 0.01, i, f"{c}  ({per} per year)", va="center", fontsize=9)
ax.set_xlabel("Citations (Scopus)")
ax.set_xlim(0, t["Cited by"].max() * 1.22)
ax.set_title("Most globally cited documents")
save(fig, "top_cited")
