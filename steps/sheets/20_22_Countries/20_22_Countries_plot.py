"""Plot of the sheet "20_22_Countries": documents and total citations of the ten most productive countries
Input : 20_22_Countries.csv in this folder (run 20_22_Countries.py first)        Output: countries_production, most_cited_countries (.png and .svg, same folder)
Run   : python3 20_22_Countries_plot.py   (needs matplotlib)
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


def read(name="20_22_Countries.csv"):
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
for col, name, title, colour in (("Documents", "countries_production", "Countries' scientific production", BLUE),
                                 ("Total Citations", "most_cited_countries", "Total citations of the same countries", GREEN)):
    d = t.sort_values(col)
    fig, ax = plt.subplots(figsize=(9, 0.5 * len(d) + 1.8))
    ax.barh(d["Countries"], d[col], color=colour)
    for i, v in enumerate(d[col]):
        ax.text(v + d[col].max() * 0.01, i, f"{v:,}", va="center")
    ax.set_xlabel(col)
    ax.set_xlim(0, d[col].max() * 1.13)
    ax.set_title(title)
    save(fig, name)
