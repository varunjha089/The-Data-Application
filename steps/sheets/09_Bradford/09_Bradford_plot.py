"""Plot of the sheet "09_Bradford": Bradford's law in the format of the study: cumulative documents against ln(rank) of the source, the empirical curve,
the log-linear fit C(r) = a + b ln(r), three zones (equal thirds of the attributed documents) and the numbered core sources.
Input : 09_Bradford.csv in this folder (run 09_Bradford.py first)        Output: bradford (.png and .svg, same folder)
Run   : python3 09_Bradford_plot.py   (needs pandas, numpy, matplotlib)
"""
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
src_df = pd.read_csv(HERE / "09_Bradford.csv", encoding="utf-8-sig")[["Source", "Documents"]].rename(columns={"Documents": "Freq"})
src_df["Rank"] = range(1, len(src_df) + 1)
src_df["CumFreq"] = src_df["Freq"].cumsum()
N_attr = int(src_df["Freq"].sum())
n_sources = len(src_df)

# zones: equal thirds of the documents; the source that crosses a boundary completes its zone
thresholds = [N_attr / 3, 2 * N_attr / 3, N_attr]
zone_labels, zone_idx = [], 0
for cum in src_df["CumFreq"]:
    zone_labels.append(f"Zone {zone_idx + 1}")
    if cum >= thresholds[zone_idx] and zone_idx < 2:
        zone_idx += 1
src_df["Zone"] = zone_labels
z1r, z2r, z3r = (src_df[src_df["Zone"] == z] for z in ("Zone 1", "Zone 2", "Zone 3"))

log_r = np.log(src_df["Rank"].values.astype(float))
cum_f = src_df["CumFreq"].values.astype(float)
slope, intercept = np.polyfit(log_r, cum_f, 1)
r2 = float(np.corrcoef(log_r, cum_f)[0, 1] ** 2)
k_geom = np.sqrt(len(z2r) / len(z1r) * len(z3r) / len(z2r))
print(f"zones {len(z1r)}/{len(z2r)}/{len(z3r)} sources, {N_attr} documents, C(r) = {intercept:.2f} + {slope:.2f} ln(r), R2 = {r2:.3f}, k = {k_geom:.2f}")

# Abbreviation map (applied after title-casing + minor-word lowering + country strip)
ABBREV = {
    'Remote Sensing'                : 'Remote Sensing (MDPI)',
    'Water'                         : 'Water (MDPI)',
    'Sensors'                       : 'Sensors (MDPI)',
    'Ieee Transactions on Geoscience and Remote Sensing' : 'IEEE Trans. Geosci. Remote Sens.',
    'Ieee Journal of Selected Topics in Applied Earth Observations and Remote Sensing' : 'IEEE JSTARS',
    'Isprs Journal of Photogrammetry and Remote Sensing' : 'ISPRS J. Photogramm. Remote Sens.',
    'International Journal of Applied Earth Observation and Geoinformation' : 'Int. J. Appl. Earth Obs. Geoinf.',
    'Hydrology and Earth System Sciences' : 'Hydrology and Earth System Sci.',
    'International Geoscience and Remote Sensing Symposium' : 'Int. Geosci. Remote Sens. Symp. (IGARSS)',
    'Proceedings of Spie - the International Society for Optical Engineering' : 'Proc. SPIE',
    'Science of the Total Environment' : 'Sci. Total Environ.',
    'Environmental Monitoring and Assessment' : 'Environ. Monit. Assess.',
}

def make_label(src):
    label = src.strip().title()
    for word in ('Of','The','And','In','For','On','A','An','To','By','At','From','With'):
        label = label.replace(f' {word} ', f' {word.lower()} ')
    label = re.sub(r'\s*\([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\)$', '', label)
    return ABBREV.get(label, label)

# Zone boundary ranks
z1_last = int(z1r['Rank'].max())
z2_last = int(z2r['Rank'].max())
z1_x    = np.log(z1_last)
z2_x    = np.log(z2_last)
x_max   = np.log(src_df['Rank'].max()) + 0.25
Y_MAX   = int(N_attr * 1.18)

# Fit line
x_fit = np.linspace(0.001, np.log(src_df['Rank'].max()) + 0.15, 600)
y_fit = intercept + slope * x_fit

# Core labels
core_labels = [make_label(s) for s in z1r['Source'].values]
core_x      = np.log(z1r['Rank'].values.astype(float))
core_y      = z1r['CumFreq'].values.astype(float)

fig, ax = plt.subplots(figsize=(10, 6.2))

# Zone shading
ax.axvspan(0,    z1_x, alpha=0.09, color='#2980b9', zorder=1)
ax.axvspan(z1_x, z2_x, alpha=0.04, color='#7f8c8d', zorder=1)
ax.axvspan(z2_x, x_max, alpha=0.02, color='#7f8c8d', zorder=1)

# Empirical curve
ax.plot(np.log(src_df['Rank'].values), src_df['CumFreq'].values,
        color='#1a1a2e', linewidth=1.6, zorder=3, label='Empirical cumulative curve')

# Fit line
ax.plot(x_fit, y_fit, color='#c0392b', linewidth=1.0, linestyle='--', zorder=2,
        label=f'$C(r)={intercept:.2f}+{slope:.2f}\\,\\ln(r)$   $R^2={r2:.3f}$')

# Zone boundaries
for x_bnd in [z1_x, z2_x]:
    ax.axvline(x_bnd, color='#444444', linestyle=':', linewidth=0.8, zorder=2)

# Zone labels
ax.text(z1_x/2,          28, f'Core\n({len(z1r)} sources)',   ha='center', va='bottom', fontsize=9, fontstyle='italic', color='#34495e')
ax.text((z1_x+z2_x)/2,  28, f'Zone 2\n({len(z2r)} sources)', ha='center', va='bottom', fontsize=9, fontstyle='italic', color='#34495e')
ax.text((z2_x+x_max)/2, 28, f'Zone 3\n({len(z3r)} sources)', ha='center', va='bottom', fontsize=9, fontstyle='italic', color='#34495e')

# Core points
ax.scatter(core_x, core_y, s=40, color='#2980b9', zorder=5, edgecolors='white', linewidth=0.6)

# Number labels — centred on the dot, offset in POINTS so they clear it at any data scale:
# 13 pt above for ranks 1–7; ranks 8–11 are bunched (freq 16–18), so they alternate: 8 and 10 below (17 pt), 9 and 11 above (16 pt)
offsets = [(0, 13)] * len(core_x)
for i in range(7, len(core_x)):
    offsets[i] = (0, 16) if i % 2 == 0 else (0, -17)

for i, (cx, cy) in enumerate(zip(core_x, core_y)):
    dx, dy = offsets[i]
    va = 'bottom' if dy > 0 else 'top'
    ax.annotate(str(i + 1), xy=(cx, cy), xytext=(dx, dy),
                textcoords='offset points',
                ha='center', va=va, fontsize=6.5,
                color='#2980b9', fontweight='bold', zorder=6)

# Core legend box
legend_text = '\n'.join([f'{i+1:>2}. {lbl}' for i, lbl in enumerate(core_labels)])
ax.text(0.06, Y_MAX * 0.96, legend_text,
        fontsize=7.2, va='top', ha='left', family='monospace', color='#1a1a2e',
        linespacing=1.55,
        bbox=dict(boxstyle='round,pad=0.4', fc='white', ec='#aaaaaa', linewidth=0.6, alpha=0.88),
        zorder=7)

# Axes
ax.set_xlim(-0.08, x_max)
ax.set_ylim(0, Y_MAX)
ax.set_xlabel(r'Source $\ln(\mathrm{Rank})$', fontsize=11)
ax.set_ylabel('Cumulative Number of Articles', fontsize=11)
ax.set_title(
    "Bradford's Law — WM-RS Corpus (2016–2025)\n"
    f"$k={k_geom:.2f}$   |   $R^2={r2:.3f}$   |   {n_sources} named sources,  $N_{{\\mathrm{{attr}}}}={N_attr}$",
    fontsize=11, fontweight='bold')

ax.yaxis.grid(True, linewidth=0.4, alpha=0.45)
ax.set_axisbelow(True)
ax.spines[['top','right']].set_visible(False)
ax.tick_params(axis='both', labelsize=9)
ax.legend(fontsize=8.5, loc='upper left', bbox_to_anchor=(0.003, 0.60),
          framealpha=0.85, edgecolor='#aaaaaa')

fig.tight_layout()
for ext in ('png', 'svg'):
    fig.savefig(HERE / f'bradford.{ext}', dpi=300, bbox_inches='tight')
plt.close()
print('written bradford.png and bradford.svg')

