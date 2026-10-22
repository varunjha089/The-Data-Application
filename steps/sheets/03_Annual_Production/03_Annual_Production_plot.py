"""Plot of the sheet "03_Annual_Production": documents (bars) and total citations (line) per year
Input : 03_Annual_Production.csv in this folder (run 03_Annual_Production.py first)        Output: annual_production (.png and .svg, same folder)
Run   : python3 03_Annual_Production_plot.py   (needs matplotlib)
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


def read(name="03_Annual_Production.csv"):
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
fig, ax = plt.subplots(figsize=(10, 5.5))
ax.bar(t["Year"].astype(str), t["Documents"], color=BLUE, width=0.6, label="Documents")
ax.set_xlabel("Year")
ax.set_ylabel("Documents")
ax2 = ax.twinx()
ax2.plot(t["Year"].astype(str), t["Total Citations"], color=ORANGE, marker="o", lw=2.5, label="Total citations")
ax2.set_ylabel("Total citations")
ax2.grid(False)
ax2.spines["right"].set_visible(True)
h1, l1 = ax.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2, frameon=False)
ax.set_title("Annual scientific production")
save(fig, "annual_production")
