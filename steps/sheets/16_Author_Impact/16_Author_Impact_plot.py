"""Plot of the sheet "16_Author_Impact": the h-index of the authors of the table, in the order of the table (by h-index or by documents, see the sheet)
Input : 16_Author_Impact.csv in this folder (run 16_Author_Impact.py first)        Output: author_h_index (.png and .svg, same folder)
Run   : python3 16_Author_Impact_plot.py   (needs matplotlib)
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


def read(name="16_Author_Impact.csv"):
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
fig, ax = plt.subplots(figsize=(10, 0.42 * len(t) + 1.8))
ax.barh([short(a, 40) for a in t["Author"]], t["h_index"], color=BLUE)
for i, (h, n, tc) in enumerate(zip(t["h_index"], t["NP"], t["TC"])):
    ax.text(h + 0.08, i, f"{n} papers, {tc} citations", va="center", fontsize=9)
ax.set_xlabel("h-index (computed on this data set)")
ax.set_xlim(0, t["h_index"].max() * 1.6)
ax.set_title(f"Authors' local impact: h-index of the {len(t)} authors of the table")
save(fig, "author_h_index")
