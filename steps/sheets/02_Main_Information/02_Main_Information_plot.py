"""Plot of the sheet "02_Main_Information": documents by document type
Input : 02_Main_Information.csv in this folder (run 02_Main_Information.py first)        Output: document_types (.png and .svg, same folder)
Run   : python3 02_Main_Information_plot.py   (needs matplotlib)
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


def read(name="02_Main_Information.csv"):
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
d = t[(t["Section"] == "Document types") & (t["Parameter"] != "Total")].copy()
d["Value"] = pd.to_numeric(d["Value"])
total = d["Value"].sum()
fig, ax = plt.subplots(figsize=(9, 0.55 * len(d) + 1.6))
ax.barh(d["Parameter"][::-1], d["Value"][::-1], color=BLUE)
for i, v in enumerate(d["Value"][::-1]):
    ax.text(v + total * 0.005, i, f"{v}  ({v / total * 100:.1f}%)", va="center")
ax.set_xlabel("Documents")
ax.set_title("Documents by document type")
ax.set_xlim(0, d["Value"].max() * 1.22)
save(fig, "document_types")
