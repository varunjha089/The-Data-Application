"""Plot of the sheet "04_Avg_Citations": mean citations per paper and per year of age
Input : 04_Avg_Citations.csv in this folder (run 04_Avg_Citations.py first)        Output: average_citations_per_year (.png and .svg, same folder)
Run   : python3 04_Avg_Citations_plot.py   (needs matplotlib)
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


def read(name="04_Avg_Citations.csv"):
    return pd.read_csv(HERE / name, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype={"Author ID": str})


def short(text, n=48):
    text = str(text)
    return text if len(text) <= n else text[: n - 1] + "..."


def save(fig, name):
    fig.savefig(HERE / f"{name}.png", dpi=150, bbox_inches="tight")
    fig.savefig(HERE / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)
    print(f"written {name}.png and {name}.svg")


t = read()
fig, ax = plt.subplots(figsize=(10, 5.2))
ax.plot(t["Year"].astype(str), t["Mean Citations per Year"], color=BLUE, marker="o", lw=2.5)
for x, v in zip(t["Year"].astype(str), t["Mean Citations per Year"]):
    ax.annotate(f"{v:.2f}", (x, v), textcoords="offset points", xytext=(0, 9), ha="center", fontsize=10)
ax.set_ylim(0, t["Mean Citations per Year"].max() * 1.25)
ax.set_xlabel("Publication year")
ax.set_ylabel("Mean citations per year")
ax.set_title("Average citations per year (citations per paper divided by the years since publication)")
save(fig, "average_citations_per_year")
