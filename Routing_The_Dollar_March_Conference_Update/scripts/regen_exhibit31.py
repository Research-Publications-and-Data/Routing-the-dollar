"""Regenerate Exhibit 31 (weekend day-of-week) with corrected SVB red line.

Uses the already-computed data from weekend_analysis_expanded.csv.
Only regenerates the chart — does not recompute statistics.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────
BASE = Path('/home/user/Claude/handoff')
PROC = BASE / 'data' / 'processed'
EXHI = BASE / 'exhibits'
MEDIA = BASE / 'media'
MEDIA_V25 = Path('/home/user/Claude/regulating_routers_v25/media')
for d in [EXHI, MEDIA, MEDIA_V25]:
    d.mkdir(parents=True, exist_ok=True)

# ── Style ────────────────────────────────────────────────────
NAVY = '#003366'
GOLD = '#CC8800'
RED = '#CC3333'

matplotlib.rcParams.update({
    'font.family': 'serif',
    'font.size': 10,
    'axes.titlesize': 11,
    'axes.titleweight': 'bold',
    'axes.labelsize': 10,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.grid': True,
    'grid.alpha': 0.3,
    'grid.linewidth': 0.5,
})

# ── Load data ────────────────────────────────────────────────
df = pd.read_csv(PROC / 'weekend_analysis_expanded.csv')
df['date'] = pd.to_datetime(df['date'])
df = df.set_index('date')

dow_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

# ── SVB crisis week: Mar 6-12 (Mon→Sun, one clean trajectory) ──
svb_chart = df[(df.index >= '2023-03-06') & (df.index <= '2023-03-12')].sort_index()
assert len(svb_chart) == 7, f"Expected 7 SVB dates, got {len(svb_chart)}"

print("SVB crisis week (Mar 6-12) T1 shares:")
for d, row in svb_chart.iterrows():
    print(f"  {d.date()} ({row['day_of_week'][:3]}): {row['t1_share']*100:.1f}%")

# ── SVB Fri→Sat stats (for Panel B) ──
df_c = df.copy()
df_c['dow_num'] = pd.Categorical(df_c['day_of_week'], categories=dow_order, ordered=True).codes
df_c['prior_dow'] = df_c['dow_num'].shift(1)
df_c['transition'] = df_c.apply(
    lambda r: f"{int(r['prior_dow'])}\u2192{int(r['dow_num'])}" if pd.notna(r['prior_dow']) else None, axis=1)

non_svb_fri_sat = df_c[(df_c['transition'] == '4\u21925') & (~df_c['is_svb_window'])]['t1_change_from_prior'].dropna()
svb_mar11 = df_c[df_c.index.day == 11]
svb_mar11 = svb_mar11[(svb_mar11.index.month == 3) & (svb_mar11.index.year == 2023)]
svb_fri_sat_change = float(svb_mar11['t1_change_from_prior'].iloc[0]) if len(svb_mar11) > 0 else np.nan
svb_fri_sat_z = (svb_fri_sat_change - non_svb_fri_sat.mean()) / non_svb_fri_sat.std() if non_svb_fri_sat.std() > 0 else np.nan

print(f"\nSVB Fri\u2192Sat change: {svb_fri_sat_change*100:.1f} pp (z={svb_fri_sat_z:.1f}\u03c3)")

# ── Exhibit: Two-panel ──────────────────────────────────────
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6.5, 6.0), gridspec_kw={'height_ratios': [1.2, 1]})

# Panel A: Box-and-whisker by day of week
dow_data = [df[df['day_of_week'] == d]['t1_share'].values * 100 for d in dow_order]
bp = ax1.boxplot(dow_data, labels=[d[:3] for d in dow_order], patch_artist=True,
                 widths=0.6, showfliers=False)
for patch, day in zip(bp['boxes'], dow_order):
    patch.set_facecolor(GOLD if day in ('Saturday', 'Sunday') else NAVY)
    patch.set_alpha(0.6)
for median in bp['medians']:
    median.set_color('black')
    median.set_linewidth(1.5)

# Overlay SVB crisis week (Mar 6-12: one clean Mon→Sun trajectory)
svb_x = [dow_order.index(d) + 1 for d in svb_chart['day_of_week']]
svb_y = svb_chart['t1_share'].values * 100
ax1.plot(svb_x, svb_y, 'o-', color=RED, linewidth=2, markersize=5, zorder=5, label='SVB week (Mar 6\u201312)')
ax1.legend(fontsize=8, loc='lower left')
ax1.set_ylabel('Tier 1 Volume Share (%)')
ax1.set_title('Tier 1 Share by Day of Week')

# Panel B: Histogram of Fri→Sat changes + SVB marker
ax2.hist(non_svb_fri_sat.values * 100, bins=25, color=NAVY, alpha=0.6, edgecolor='white',
         label='Non-SVB Fri\u2192Sat')
ax2.axvline(svb_fri_sat_change * 100, color=RED, linewidth=2, linestyle='--',
            label=f'SVB: {svb_fri_sat_change*100:.1f} pp (z={svb_fri_sat_z:.1f}\u03c3)')
ax2.set_xlabel('Fri\u2192Sat T1 Share Change (pp)')
ax2.set_ylabel('Frequency')
ax2.set_title('Distribution of Friday-to-Saturday Tier 1 Share Changes')
ax2.legend(fontsize=8)

fig.tight_layout()

# Save to all output locations
for d in [EXHI, MEDIA, MEDIA_V25]:
    outpath = d / 'exhibit_weekend_dayofweek.png'
    fig.savefig(outpath, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"Saved: {outpath}")
plt.close(fig)

# ── Verification ─────────────────────────────────────────────
print("\n=== VERIFICATION ===")
expected = {
    'Mon': 55.5, 'Tue': 57.8, 'Wed': 41.6, 'Thu': 48.9,
    'Fri': 62.5, 'Sat': 29.9, 'Sun': 13.2
}
for i, (day_abbr, exp_val) in enumerate(expected.items()):
    actual = svb_y[i]
    match = abs(actual - exp_val) < 0.5
    print(f"  {day_abbr}: actual={actual:.1f}%, expected~{exp_val}% {'OK' if match else 'MISMATCH'}")

# Verify the trajectory shape: rises Mon-Fri, crashes Fri-Sat-Sun
fri_idx = 4  # 0-indexed
assert svb_y[fri_idx] > svb_y[0], "Fri should be higher than Mon"
assert svb_y[fri_idx] > svb_y[fri_idx + 1], "Fri→Sat should drop"
assert svb_y[fri_idx + 1] > svb_y[fri_idx + 2], "Sat→Sun should drop"
print("\n  Shape: baseline \u2192 spike \u2192 crash \u2192 nadir \u2714")
print("  NOT a monotonic decline \u2714")
print("  Label reads 'SVB week (Mar 6\u201312)' \u2714")
print(f"  Panel B unchanged: SVB Fri\u2192Sat = {svb_fri_sat_change*100:.1f} pp \u2714")
print("\nDone.")
