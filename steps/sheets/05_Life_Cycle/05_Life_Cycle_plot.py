"""Plot of the sheet "05_Life_Cycle": cumulative documents and the fitted logistic (S-shaped) curve
Input : 05_Life_Cycle.csv in this folder (run 05_Life_Cycle.py first)        Output: life_cycle (.png and .svg, same folder)
Run   : python3 05_Life_Cycle_plot.py   (needs matplotlib)
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


def read(name="05_Life_Cycle.csv"):
    return pd.read_csv(HERE / name, encoding="utf-8-sig", keep_default_na=False, na_values=[""], dtype={"Author ID": str})


def short(text, n=48):
    text = str(text)
    return text if len(text) <= n else text[: n - 1] + "..."


def save(fig, name):
    fig.savefig(HERE / f"{name}.png", dpi=150, bbox_inches="tight")
    fig.savefig(HERE / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)
    print(f"written {name}.png and {name}.svg")


import argparse
import datetime
from matplotlib.ticker import FormatStrFormatter, MaxNLocator
import numpy as np


# Year axes: a corpus can span 10 years or 55, so the axis must not draw one label per year. Numeric axis with about 10 round ticks, early-access years shaded, and a range
# of years you can choose (--from-year / --to-year, 0 = automatic; the application passes your choice). Automatic start = the first year at which 1% of the papers are reached;
# the years left out are named in the axis label. Only the picture is cut, never the table.
def year_args():
    """the first and last year asked for (0 = automatic)"""
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-year", type=int, default=0)
    ap.add_argument("--to-year", type=int, default=0)
    a, _ = ap.parse_known_args()
    lo, hi = a.from_year, a.to_year
    return (hi, lo) if lo and hi and lo > hi else (lo, hi)


def year_start(years, size, share=0.01):
    """first year at which the running total of `size` (papers per year) reaches `share` of the whole"""
    years, cum = list(years), np.cumsum(np.asarray(size, dtype=float))
    return years[int(np.argmax(cum >= share * cum[-1]))] if len(cum) and cum[-1] > 0 else (years[0] if years else 0)


def year_window(years, size, lo=0, hi=0):
    """first and last year drawn: the chosen ones, else automatic (from the 1% year to the last year of the data)"""
    start, end = lo or year_start(years, size), hi or max(years)
    if start > end:
        raise SystemExit(f"No year to draw: the range {start}-{end} is empty.")
    return start, end


def year_keep(years, start, end):
    """True for the years inside the window"""
    return [start <= y <= end for y in years]


def year_label(years, size, start, end, label="Year"):
    """axis label that says which years were left out (and how many papers they hold)"""
    years, size = list(years), np.asarray(size, dtype=float)
    hid = [y for y in years if y < start or y > end]
    if not hid or size.sum() == 0:
        return label
    n = size[[y < start or y > end for y in years]].sum()
    parts = [f"{min(y for y in hid if y < start)}-{start - 1}" if any(y < start for y in hid) else "", f"{end + 1}-{max(y for y in hid if y > end)}" if any(y > end for y in hid) else ""]
    return f"{label}   ({', '.join(p for p in parts if p)} not shown: {n:.0f} {'paper' if n == 1 else 'papers'}, {100 * n / size.sum():.1f}%)"


def year_axis(ax, years, pad=0.6):
    """about 10 integer ticks whatever the span; years after the current year (early access) are shaded"""
    ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=10, steps=[1, 2, 5, 10]))
    ax.xaxis.set_major_formatter(FormatStrFormatter("%d"))
    ax.set_xlim(min(years) - pad, max(years) + pad)
    this = datetime.date.today().year
    if max(years) > this:
        ax.axvspan(this + 0.5, max(years) + 0.5, color="#888888", alpha=0.13, lw=0, zorder=0)
        ax.text((this + max(years) + 1) / 2, 0.05, "early access", transform=ax.get_xaxis_transform(), rotation=90, va="bottom", ha="center", fontsize=8, color="#555555")


def year_rows(df, col="Year"):
    """the rows of a table whose year is inside the years you chose (all rows when you chose nothing)"""
    lo, hi = year_args()
    out = df[(df[col] >= (lo or df[col].min())) & (df[col] <= (hi or df[col].max()))]
    if out.empty:
        raise SystemExit(f"No data between {lo or 'the first year'} and {hi or 'the last year'}.")
    return out


t = read()
size = np.diff(t["Cumulative"].to_numpy(dtype=float), prepend=0)
start, end = year_window(t["Year"], size, *year_args())
xlab = year_label(t["Year"], size, start, end)
t = t[year_keep(t["Year"], start, end)]
p = read("05_Life_Cycle_parameters.csv").set_index("Parameter")["Value"]
fig, ax = plt.subplots(figsize=(10, 5.5))
ax.plot(t["Year"], t["Cumulative"], color=ORANGE, marker="o", lw=2.5, label="Cumulative documents")
ax.plot(t["Year"], t["Fitted"], color=GREY, marker="o", lw=2, ls="--", label="Fitted logistic curve")
year_axis(ax, t["Year"])
ax.set_xlabel(xlab)
ax.set_ylabel("Cumulative documents")
ax.legend(frameon=False, loc="upper left")
ax.text(0.02, 0.70, f"K = {p['k']:.0f}   r = {p['r']:.3f}   t0 = {p['t0']:.1f}\nR2 = {p['R2']:.4f}\npeak output = {p['Peak annual output']:.0f} per year\n90% of K reached in {p['Year 90% of K is reached']:.1f}",
        transform=ax.transAxes, va="top", fontsize=11)
ax.set_title("Life cycle of scientific production")
save(fig, "life_cycle")
