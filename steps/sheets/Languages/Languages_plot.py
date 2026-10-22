"""Plot of the sheet "Languages": pie chart of the languages of the papers (the style of the document-type and open-access pies)
Input : Languages.csv in this folder (run Languages.py first)        Output: languages_pie (.png and .svg, same folder)
Languages beyond your choice of how many are shown are grouped as "Other languages" (column "Shown as" of the CSV).
Run   : python3 Languages_plot.py   (needs matplotlib, pandas)
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent


def read(name):
    return pd.read_csv(HERE / name, encoding="utf-8-sig", keep_default_na=False, na_values=[""])


def pie(t, label, colors, title, out, pct_min):
    fig, ax = plt.subplots(figsize=(6, 5))
    _, _, auto = ax.pie(t["Papers"], labels=None, autopct=lambda p: f"{p:.1f}%" if p > pct_min else "", colors=colors, startangle=90, pctdistance=0.78,
                        wedgeprops={"linewidth": 0.5, "edgecolor": "white"})
    for a in auto:
        a.set_fontsize(8)
    ax.legend([f"{l} ({v})" for l, v in zip(t[label], t["Papers"])], loc="lower center", bbox_to_anchor=(0.5, -0.22), ncol=2, fontsize=8)
    ax.set_title(f"{title} (N={int(t['Papers'].sum()):,})", fontweight="bold")
    for ext in ("png", "svg"):
        fig.savefig(HERE / f"{out}.{ext}", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"written {out}.png and {out}.svg")


t = read("Languages.csv")
t = t.groupby("Shown as", sort=False)["Papers"].sum().reset_index()           # keeps the order of the CSV (largest first, "Other languages" last)
COLORS = ["#1a5276", "#e67e22", "#2e86c1", "#27ae60", "#8e44ad", "#c0392b", "#f1c40f", "#16a085", "#7f8c8d"]
colors = [("#aab7b8" if s == "Other languages" else COLORS[i % (len(COLORS) - 1)]) for i, s in enumerate(t["Shown as"])]
pie(t, "Shown as", colors, "Languages of the Papers", "languages_pie", 3)
