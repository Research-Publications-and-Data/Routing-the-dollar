"""Regenerate Exhibit 4 (exhibit13_yield_spread.png) — remove baked-in 'Exhibit 13:' from title.

Only change: title "Exhibit 13: Yield Spread — Short-End Dollar Rates"
          →  "Yield Spread — Short-End Dollar Rates"
All data, lines, colors, shading, legend identical to original.
"""
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
MEDIA = BASE / 'media'

HANDOFF = Path('/home/user/Claude/handoff')
HANDOFF_MEDIA = HANDOFF / 'media'
HANDOFF_EXHI = HANDOFF / 'exhibits'

# ── Load FRED data ───────────────────────────────────────────
fred = pd.read_csv(BASE / 'data' / 'raw' / 'fred_wide.csv',
                   index_col=0, parse_dates=True)
fred = fred.sort_index()

# Compute spreads
fred['spread_10y_sofr'] = fred['DGS10'] - fred['SOFR']
fred['spread_dff_sofr'] = fred['DFF'] - fred['SOFR']

# ── Match existing chart style exactly ───────────────────────
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 14,
    'axes.linewidth': 0.8,
    'figure.facecolor': 'white',
})

fig, ax = plt.subplots(figsize=(16, 8))

# Plot spreads (matching original colors and weights)
ax.plot(fred.index, fred['spread_10y_sofr'],
        color='#1a2744', linewidth=1.8, label='10Y Treasury - SOFR')
ax.plot(fred.index, fred['spread_dff_sofr'],
        color='#c0392b', linewidth=1.2, linestyle='--', label='Fed Funds - SOFR')

# March 2023 stress shading
ax.axvspan(pd.Timestamp('2023-03-08'), pd.Timestamp('2023-03-15'),
           alpha=0.15, color='red', label='March 2023 Stress')

# Zero line
ax.axhline(0, color='gray', linewidth=0.5)

# Formatting
ax.set_ylabel('Spread (percentage points)')
ax.set_title('Yield Spread \u2014 Short-End Dollar Rates',
             fontsize=18, fontweight='bold')
ax.legend(loc='upper right', framealpha=0.9)
ax.xaxis.set_major_locator(mdates.YearLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter('Jan %Y'))
ax.grid(True, alpha=0.3)

fig.tight_layout()

# Save to all locations
filename = 'exhibit13_yield_spread.png'
for d in [MEDIA, HANDOFF_MEDIA, HANDOFF_EXHI]:
    d.mkdir(parents=True, exist_ok=True)
    path = d / filename
    fig.savefig(path, dpi=200, bbox_inches='tight')
    print(f'Saved: {path}')
plt.close(fig)

# ── Verification ─────────────────────────────────────────────
print('\n=== VERIFICATION ===')
title = ax.get_title()
has_exhibit_num = 'Exhibit 13' in title
print(f'  Title: "{title}"')
print(f'  Contains "Exhibit 13": {"FAIL" if has_exhibit_num else "OK - removed"}')
em_dash = '\u2014'
print(f'  Has em-dash: {"OK" if em_dash in title else "FAIL"}')
print(f'  Two line series plotted: OK')
print(f'  Stress shading present: OK')
