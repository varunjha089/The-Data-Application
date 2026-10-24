"""Plot of the sheet "04_Avg_Citations": mean citations per paper and per year of age
Input : 04_Avg_Citations.csv in this folder (run 04_Avg_Citations.py first)        Output: average_citations_per_year (.png and .svg, same folder)
Run   : python3 04_Avg_Citations_plot.py   (needs matplotlib)
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


def read(name="04_Avg_Citations.csv"):
    return pd.read_csv(HERE / name, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype={"Author ID": str})


def short(text, n=48):
    text = str(text)
    return text if len(text) <= n else text[: n - 1] + "..."


def save(fig, name):
    fig.savefig(HERE / f"{name}.png", dpi=150, bbox_inches="tight")
    fig.savefig(HERE / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)
    print(f"written {name}.png and {name}.svg")


import datetime
from matplotlib.ticker import FormatStrFormatter, MaxNLocator
import numpy as np


# Year axes: a corpus can span 10 years or 55, so the axis must not draw one label per year. Numeric axis with about 10 round ticks, an axis that starts where
# the data does (the first year at which 1% of the papers are reached; the hidden years are named in the axis label), early-access years shaded.
def year_start(years, size, share=0.01):
    """first year at which the running total of `size` (papers per year) reaches `share` of the whole"""
    years, cum = list(years), np.cumsum(np.asarray(size, dtype=float))
    return years[int(np.argmax(cum >= share * cum[-1]))] if len(cum) and cum[-1] > 0 else (years[0] if years else 0)


def year_label(years, size, start, label="Year"):
    """axis label that says which early years were left out (and how many papers they hold)"""
    years, size = list(years), np.asarray(size, dtype=float)
    hid = size[[y < start for y in years]]
    return label if not len(hid) or start <= min(years) else f"{label}   ({min(years)}-{start - 1} not shown: {hid.sum():.0f} {"paper" if hid.sum() == 1 else "papers"}, {100 * hid.sum() / size.sum():.1f}%)"


def year_axis(ax, years, pad=0.6):
    """about 10 integer ticks whatever the span; years after the current year (early access) are shaded"""
    ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=10, steps=[1, 2, 5, 10]))
    ax.xaxis.set_major_formatter(FormatStrFormatter("%d"))
    ax.set_xlim(min(years) - pad, max(years) + pad)
    this = datetime.date.today().year
    if max(years) > this:
        ax.axvspan(this + 0.5, max(years) + 0.5, color="#888888", alpha=0.13, lw=0, zorder=0)
        ax.text((this + max(years) + 1) / 2, 0.05, "early access", transform=ax.get_xaxis_transform(), rotation=90, va="bottom", ha="center", fontsize=8, color="#555555")


ALLT = t = read()
size = t["Documents"] if "Documents" in t.columns else pd.Series(1.0, index=t.index)
start = year_start(t["Year"], size)
xlab = year_label(t["Year"], size, start, "Publication year")
t = t[t["Year"] >= start]
fig, ax = plt.subplots(figsize=(10, 5.2))
ax.plot(t["Year"], t["Mean Citations per Year"], color=BLUE, marker="o", lw=2.5)
for x, v in zip(t["Year"], t["Mean Citations per Year"]):
    ax.annotate(f"{v:.2f}", (x, v), textcoords="offset points", xytext=(0, 9), ha="center", fontsize=10)
ax.set_ylim(0, t["Mean Citations per Year"].max() * 1.25)
ax.set_xlabel(xlab)
year_axis(ax, t["Year"])
ax.set_ylabel("Mean citations per year")
ax.set_title("Average citations per year (citations per paper divided by the years since publication)")
save(fig, "average_citations_per_year")
