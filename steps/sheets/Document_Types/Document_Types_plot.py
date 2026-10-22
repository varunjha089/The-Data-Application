"""Plot of the sheet "Document_Types": pie chart of the document types (the style of the EDA notebook, figure S1_doctype)
Input : Document_Types.csv in this folder (run Document_Types.py first)        Output: document_types_pie (.png and .svg, same folder)
Run   : python3 Document_Types_plot.py   (needs matplotlib, pandas)
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


t = read("Document_Types.csv")
COLORS = ["#1a5276", "#2e86c1", "#85c1e9", "#aab7b8", "#d5d8dc",                      # the five colours of the notebook, then one more for each further type
          "#7d3c98", "#f5b041", "#52be80", "#e74c3c", "#5d6d7e"]
pie(t, "Document Type", COLORS[: len(t)], "Document Types", "document_types_pie", 3)
