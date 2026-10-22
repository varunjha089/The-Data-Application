"""Plot of the sheet "05_Life_Cycle": cumulative documents and the fitted logistic (S-shaped) curve
Input : 05_Life_Cycle.csv in this folder (run 05_Life_Cycle.py first)        Output: life_cycle (.png and .svg, same folder)
Run   : python3 05_Life_Cycle_plot.py   (needs matplotlib)
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


def read(name="05_Life_Cycle.csv"):
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
p = read("05_Life_Cycle_parameters.csv").set_index("Parameter")["Value"]
fig, ax = plt.subplots(figsize=(10, 5.5))
ax.plot(t["Year"], t["Cumulative"], color=ORANGE, marker="o", lw=2.5, label="Cumulative documents")
ax.plot(t["Year"], t["Fitted"], color=GREY, marker="o", lw=2, ls="--", label="Fitted logistic curve")
ax.set_xticks(t["Year"])
ax.set_xlabel("Year")
ax.set_ylabel("Cumulative documents")
ax.legend(frameon=False, loc="upper left")
ax.text(0.02, 0.70, f"K = {p['k']:.0f}   r = {p['r']:.3f}   t0 = {p['t0']:.1f}\nR2 = {p['R2']:.4f}\npeak output = {p['Peak annual output']:.0f} per year\n90% of K reached in {p['Year 90% of K is reached']:.1f}",
        transform=ax.transAxes, va="top", fontsize=11)
ax.set_title("Life cycle of scientific production")
save(fig, "life_cycle")
