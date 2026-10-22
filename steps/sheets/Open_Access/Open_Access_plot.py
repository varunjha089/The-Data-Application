"""Plot of the sheet "Open_Access": pie chart of the open access status (the style of the EDA notebook, figure S1_oa)
Input : Open_Access.csv in this folder (run Open_Access.py first)        Output: open_access_pie (.png and .svg, same folder)
Run   : python3 Open_Access_plot.py   (needs matplotlib, pandas)
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


t = read("Open_Access.csv")
COLORS = {"Gold OA": "#f1c40f", "Hybrid Gold": "#f39c12", "Bronze OA": "#cd853f", "Green OA": "#27ae60", "Closed / Unknown": "#95a5a6"}
pie(t, "Open access class", [COLORS.get(c, "#bdc3c7") for c in t["Open access class"]], "Open Access Status", "open_access_pie", 2)
