"""Plot of the sheet "Country_Radar": radar chart of the most productive countries on five indicators (the October chart "Charts/08_Radar")
Input : Country_Radar.csv in this folder (run Country_Radar.py first)        Output: radar_countries (.png and .svg, same folder)
Each indicator is scaled so that the largest value among the 10 most productive countries = 100; the countries drawn are the ones marked "On radar" (your choice, default 5).
Run   : python3 Country_Radar_plot.py   (needs matplotlib, numpy, pandas)
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
plt.rcParams.update({"font.size": 11})
t = pd.read_csv(HERE / "Country_Radar.csv", encoding="utf-8-sig")
cols = ["Documents", "Citations", "Citations_per_doc", "h_index", "MCP_pct"]
scaled = (t[cols] / t[cols].max() * 100)
scaled.index = t["Country"]
draw = scaled[t["On radar"].to_numpy() == 1]
th = np.linspace(0, 2 * np.pi, len(cols), endpoint=False)
fig = plt.figure(figsize=(7.5, 7))
ax = fig.add_subplot(111, polar=True)
for i, (name, r) in enumerate(draw.iterrows()):
    v = r.tolist()
    ax.plot(np.append(th, th[0]), v + v[:1], lw=2, label=name, color=plt.cm.tab10(i))
    ax.fill(np.append(th, th[0]), v + v[:1], alpha=0.08, color=plt.cm.tab10(i))
ax.set_xticks(th)
ax.set_xticklabels([c.replace("_", " ") for c in cols])
ax.set_ylim(0, 100)
ax.set_yticks([25, 50, 75, 100])
ax.tick_params(axis="y", labelsize=7)
ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), frameon=False)
ax.set_title(f"Top-{len(draw)} countries on five indicators (top-{len(t)} maximum = 100)", y=1.08, fontsize=12)
fig.text(0.5, 0.03, "MCP % = share of the country's papers with 2 or more countries; h-index is country-level.", ha="center", fontsize=9, color="#555")
for ext in ("png", "svg"):
    fig.savefig(HERE / f"radar_countries.{ext}", dpi=150, bbox_inches="tight")
plt.close(fig)
print("written radar_countries.png and radar_countries.svg")
