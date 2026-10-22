"""Plot of the sheet "15_Lotka": Lotka's law: share of authors by number of papers (log-log) against the theoretical curve
Input : 15_Lotka.csv in this folder (run 15_Lotka.py first)        Output: lotka (.png and .svg, same folder)
Run   : python3 15_Lotka_plot.py   (needs matplotlib)
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


def read(name="15_Lotka.csv"):
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
p = read("15_Lotka_parameters.csv").set_index("Parameter")["Value"]
fig, ax = plt.subplots(figsize=(9, 5.5))
ax.plot(t["Documents written"], t["Proportion of Authors"], color=BLUE, marker="o", lw=2.5, label="Observed")
ax.plot(t["Documents written"], t["Lotka (β = 2)"], color=ORANGE, marker="o", lw=2, ls="--", label="Lotka with β = 2")
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("Documents written (log scale)")
ax.set_ylabel("Proportion of authors (log scale)")
ax.legend(frameon=False)
ax.text(0.04, 0.30, f"fitted β = {p['β (slope)']:.2f}\nC = {p['C']:.3f}\nR2 = {p['R²']:.3f}", transform=ax.transAxes, ha="left", va="top")
ax.set_title("Lotka's law")
save(fig, "lotka")
