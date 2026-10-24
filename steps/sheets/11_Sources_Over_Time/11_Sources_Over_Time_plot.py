"""Plot of the sheet "11_Sources_Over_Time": cumulative documents of the five most productive sources
Input : 11_Sources_Over_Time.csv in this folder (run 11_Sources_Over_Time.py first)        Output: sources_over_time and sources_timeline (.png and .svg, same folder)
Run   : python3 11_Sources_Over_Time_plot.py   (needs matplotlib)
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


def read(name="11_Sources_Over_Time.csv"):
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


t = read().drop(columns=["Grand Total"])
size = np.diff(t.iloc[:, 1:].to_numpy(dtype=float), axis=0, prepend=0).sum(axis=1)
start = year_start(t["Year"], size)
xlab = year_label(t["Year"], size, start)
t = t[(t["Year"] >= start).to_numpy()]
fig, ax = plt.subplots(figsize=(10, 5.8))
for col, c in zip(t.columns[1:], [BLUE, ORANGE, GREEN, RED, PURPLE, GREY]):
    ax.plot(t["Year"], t[col], marker="o", lw=2.4, color=c, label=short(col, 55))
ax.set_xlabel(xlab)
year_axis(ax, t["Year"])
ax.set_ylabel("Cumulative documents")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=1, frameon=False, fontsize=10)
ax.set_title("Sources' production over time")
save(fig, "sources_over_time")

# second option: the timeline of Biblioshiny: one row per source, a line from the first to the last year, a bubble for every year with papers
# (size = papers of the year, darker = more citations per year); the most productive on top
tl = read("11_Source_Timeline.csv")
order = list(dict.fromkeys(tl["Source title"]))
ypos = {a: len(order) - 1 - i for i, a in enumerate(order)}
from matplotlib.colors import LinearSegmentedColormap
BLUES_FROM_LIGHT = LinearSegmentedColormap.from_list("blues_light", ["#BFD5EA", "#0B2F6B"])      # the lightest bubble stays visible on white
def bubble(n):
    """area of a bubble: grows with the papers of the year; the largest value of this plot always gets the same (biggest) size"""
    return 50 + 650 * pd.Series(n) / tl["Papers"].max() if hasattr(n, "__len__") else 50 + 650 * n / tl["Papers"].max()


fig, ax = plt.subplots(figsize=(11, 0.5 * len(order) + 2.2))
for a, g in tl.groupby("Source title"):
    ax.plot([g["Year"].min(), g["Year"].max()], [ypos[a]] * 2, color="#C9A0A0", lw=2.5, zorder=1, solid_capstyle="round")
sc = ax.scatter(tl["Year"], [ypos[a] for a in tl["Source title"]], s=bubble(tl["Papers"]), c=tl["TC per year"], cmap=BLUES_FROM_LIGHT, vmin=0, vmax=tl["TC per year"].max(), alpha=0.85, edgecolor="#1F3F6B", linewidth=0.6, zorder=2)
ax.set_yticks([ypos[a] for a in order], [short(a, 45) for a in order], fontweight="bold")
year_axis(ax, tl["Year"])
ax.set_ylim(-0.7, len(order) - 0.3)
ax.grid(axis="y")
ax.grid(axis="x", visible=False)
ax.set_xlabel("Year")
ax.set_ylabel("Source")
ax.set_title("Sources' production over time")
cb = fig.colorbar(sc, ax=ax, pad=0.02, shrink=0.5)
cb.set_label("TC per year")
sizes = sorted({1, int(tl["Papers"].max()), max(int(tl["Papers"].max()) // 2, 1)})
ax.legend([plt.scatter([], [], s=bubble(n), c="#7FA6D0", edgecolor="#1F3F6B") for n in sizes], [str(n) for n in sizes], title="Papers", frameon=False, loc="upper left", bbox_to_anchor=(1.12, 0.35), labelspacing=1.4)
save(fig, "sources_timeline")
