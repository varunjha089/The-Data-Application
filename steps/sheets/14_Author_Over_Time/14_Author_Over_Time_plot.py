"""Plot of the sheet "14_Author_Over_Time": papers per year of the ten most productive authors (heat map)
Input : 14_Author_Over_Time.csv in this folder (run 14_Author_Over_Time.py first)        Output: authors_over_time and authors_timeline (.png and .svg, same folder)
Run   : python3 14_Author_Over_Time_plot.py   (needs matplotlib)
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


def read(name="14_Author_Over_Time.csv"):
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
years = [c for c in t.columns if c.isdigit()]
m = t[years].to_numpy()
fig, ax = plt.subplots(figsize=(10, 0.55 * len(t) + 2.2))
im = ax.imshow(m, cmap="Blues", aspect="auto")
ax.set_xticks(range(len(years)), years)
ax.set_yticks(range(len(t)), [short(a, 40) for a in t["Author"]])
ax.grid(False)
for i in range(m.shape[0]):
    for j in range(m.shape[1]):
        if m[i, j]:
            ax.text(j, i, int(m[i, j]), ha="center", va="center", color="white" if m[i, j] > m.max() * 0.55 else "black")
ax.set_xlabel("Year")
ax.set_title("Authors' production over time (papers per year)")
save(fig, "authors_over_time")

# second option: the timeline of Biblioshiny: one row per author, a line from the first to the last year, a bubble for every year with papers
# (size = papers of the year, darker = more citations per year); the 15 most productive authors, the most productive on top
tl = read("14_Author_Timeline.csv")
order = list(dict.fromkeys(tl["Author ID"]))
name = dict(zip(tl["Author ID"], tl["Author"]))
ypos = {a: len(order) - 1 - i for i, a in enumerate(order)}
from matplotlib.colors import LinearSegmentedColormap
BLUES_FROM_LIGHT = LinearSegmentedColormap.from_list("blues_light", ["#BFD5EA", "#0B2F6B"])      # the lightest bubble stays visible on white
def bubble(n):
    """area of a bubble: grows with the papers of the year; the largest value of this plot always gets the same (biggest) size"""
    return 50 + 650 * pd.Series(n) / tl["Papers"].max() if hasattr(n, "__len__") else 50 + 650 * n / tl["Papers"].max()


fig, ax = plt.subplots(figsize=(11, 0.5 * len(order) + 2.2))
for a, g in tl.groupby("Author ID"):
    ax.plot([g["Year"].min(), g["Year"].max()], [ypos[a]] * 2, color="#C9A0A0", lw=2.5, zorder=1, solid_capstyle="round")
sc = ax.scatter(tl["Year"], [ypos[a] for a in tl["Author ID"]], s=bubble(tl["Papers"]), c=tl["TC per year"], cmap=BLUES_FROM_LIGHT, vmin=0, vmax=tl["TC per year"].max(), alpha=0.85, edgecolor="#1F3F6B", linewidth=0.6, zorder=2)
ax.set_yticks([ypos[a] for a in order], [short(name[a], 30) for a in order], fontweight="bold")
ax.set_xticks(range(int(tl["Year"].min()), int(tl["Year"].max()) + 1))
ax.set_xlim(tl["Year"].min() - 0.6, tl["Year"].max() + 0.6)
ax.set_ylim(-0.7, len(order) - 0.3)
ax.grid(axis="y")
ax.grid(axis="x", visible=False)
ax.set_xlabel("Year")
ax.set_ylabel("Author")
ax.set_title("Authors' production over time")
cb = fig.colorbar(sc, ax=ax, pad=0.02, shrink=0.5)
cb.set_label("TC per year")
sizes = sorted({1, int(tl["Papers"].max()), max(int(tl["Papers"].max()) // 2, 1)})
ax.legend([plt.scatter([], [], s=bubble(n), c="#7FA6D0", edgecolor="#1F3F6B") for n in sizes], [str(n) for n in sizes], title="Papers", frameon=False, loc="upper left", bbox_to_anchor=(1.12, 0.35), labelspacing=1.4)
save(fig, "authors_timeline")
