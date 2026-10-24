"""Plot of the sheet "Institution_Bursts": the institutions with the strongest bursts, like the "citation burst history" of CiteSpace
Input : Institution_Bursts.csv and Institution_Bursts_yearly.csv in this folder (run Institution_Bursts.py first)        Output: institution_bursts (.png and .svg, same folder)
Columns: Institution, first year, strength, begin, end of the strongest burst, and a strip of the years: pale = before the first year, teal = after it, red = burst years.
Run   : python3 Institution_Bursts_plot.py   (needs matplotlib, pandas)
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Patch, Rectangle

HERE = Path(__file__).resolve().parent
PALE, TEAL, RED = "#CFECEC", "#46C7C7", "#E8372C"
t = pd.read_csv(HERE / "Institution_Bursts.csv", encoding="utf-8-sig")
y = pd.read_csv(HERE / "Institution_Bursts_yearly.csv", encoding="utf-8-sig")
if t.empty:
    fig, ax = plt.subplots(figsize=(8, 2))
    ax.axis("off")
    ax.text(0.5, 0.5, "No burst was found for the institutions at this cost (gamma).\nTry a smaller gamma or fewer papers needed.", ha="center", va="center", fontsize=12)
    for ext in ("png", "svg"):                                             # overwrite the old picture so that it cannot show an earlier result
        fig.savefig(HERE / f"institution_bursts.{ext}", dpi=150, bbox_inches="tight")
    raise SystemExit(0)
years = sorted(y["Year"].unique())
n = len(t)


def short(text, k=44):
    text = str(text)
    return text if len(text) <= k else text[: k - 1] + "..."


row_h, cell = 0.5, 0.42
nw = 0.105 * max(len(short(x, 60)) for x in t["Institution"]) + 0.7                  # width of the name column follows the longest name (one unit = about one inch)
X = {"name": 0.0, "first": nw, "strength": nw + 1.2, "begin": nw + 2.6, "end": nw + 3.8, "strip": nw + 4.9}
W = X["strip"] + cell * len(years) + 0.3
fig, ax = plt.subplots(figsize=(W, row_h * n + 2.0))
ax.set_xlim(0, W)
ax.set_ylim(-n - 1.3, 0.6)
ax.axis("off")
for key, label in (("name", "Institution"), ("first", "Year"), ("strength", "Strength"), ("begin", "Begin"), ("end", "End")):
    ax.text(X[key], 0, label, fontsize=11, fontweight="bold", va="center", ha="left")
ax.text(X["strip"], 0, f"{years[0]} - {years[-1]}", fontsize=11, fontweight="bold", va="center")
ax.plot([0, W], [-0.45, -0.45], color="#333", lw=1)
for i, r in t.iterrows():
    yy = -1 - i
    ax.text(X["name"], yy, short(r["Institution"], 60), fontsize=11, va="center")
    ax.text(X["first"], yy, str(r["First year"]), fontsize=11, va="center")
    ax.text(X["strength"], yy, f"{r['Strength']:.2f}", fontsize=11, va="center", ha="left")
    ax.text(X["begin"], yy, str(r["Begin"]), fontsize=11, va="center", fontweight="bold")
    ax.text(X["end"], yy, str(r["End"]), fontsize=11, va="center")
    ph = y[y["Institution"] == r["Institution"]].set_index("Year")["Phase"]
    for j, yr in enumerate(years):
        colour = RED if ph[yr] == "burst" else (TEAL if ph[yr] == "after the first year" else PALE)
        height = 0.42 if ph[yr] == "burst" else 0.26
        ax.add_patch(Rectangle((X["strip"] + j * cell, yy - 0.17), cell - 0.02, height, color=colour, lw=0))
    ax.plot([0, W], [yy - 0.5, yy - 0.5], color="#E6E6E6", lw=0.6)
for j, yr in enumerate(years):
    if j % 2 == 0 or len(years) <= 6:
        ax.text(X["strip"] + j * cell + 0.2, -n - 0.9, str(yr), fontsize=8, ha="center", va="center", rotation=90)
ax.legend(handles=[Patch(color=PALE, label="before the first year"), Patch(color=TEAL, label="after the first year"), Patch(color=RED, label="burst")],
          loc="lower left", frameon=False, ncol=3, fontsize=9, bbox_to_anchor=(0.0, -0.02))
ax.set_title("Top %d Institutions with the Strongest Bursts" % n, fontsize=14, fontweight="bold", loc="left")
for ext in ("png", "svg"):
    fig.savefig(HERE / f"institution_bursts.{ext}", dpi=150, bbox_inches="tight")
plt.close(fig)
print("written institution_bursts.png and institution_bursts.svg")
