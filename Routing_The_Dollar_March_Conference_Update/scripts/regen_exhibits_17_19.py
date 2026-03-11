"""Regenerate Exhibit 17 (HHI concentration) with legend moved to upper-right,
and Exhibit 19 (network topology) with title number removed + Panel B overlap fixed.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from pathlib import Path
import sys
import warnings
warnings.filterwarnings('ignore')

# ── Paths ────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent
MEDIA = BASE / 'media'
DATA_PROC = BASE / 'data' / 'processed'
EXHIBITS_DIR = BASE / 'data' / 'exhibits'

HANDOFF = Path('/home/user/Claude/handoff')
HANDOFF_MEDIA = HANDOFF / 'media'
HANDOFF_EXHI = HANDOFF / 'exhibits'

for d in [MEDIA, EXHIBITS_DIR, HANDOFF_MEDIA, HANDOFF_EXHI]:
    d.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(BASE / 'scripts'))
from utils import setup_plot_style


# ═════════════════════════════════════════════════════════════
# EXHIBIT 17: Gateway Concentration HHI — legend to upper-right
# ═════════════════════════════════════════════════════════════
def fix_exhibit17():
    print("=" * 60)
    print("EXHIBIT 17: Move top-panel legend to upper-right")
    print("=" * 60)

    hhi = pd.read_csv(DATA_PROC / 'exhibit_C2_concentration_daily_v2.csv',
                       index_col=0, parse_dates=True)
    shares = pd.read_csv(DATA_PROC / 'exhibit_C1_gateway_shares_daily_v2.csv',
                          index_col=0, parse_dates=True)

    setup_plot_style()
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    # Panel A: Tier shares stacked area
    t1 = shares.get('tier1_share_pct', 0) / 100
    t2 = shares.get('tier2_share_pct', 0) / 100
    t3 = shares.get('tier3_share_pct', 0) / 100

    ax1.stackplot(shares.index, t1, t2, t3,
                  labels=['Tier 1 (Regulated)', 'Tier 2 (Offshore)', 'Tier 3 (DeFi)'],
                  colors=['#1a5276', '#d68910', '#145a32'], alpha=0.8)
    ax1.axvspan(pd.Timestamp('2023-03-08'), pd.Timestamp('2023-03-15'),
                color='#ffcccc', alpha=0.3, label='SVB Crisis')
    ax1.set_ylabel('Share of Volume')
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'{x*100:.0f}%'))
    ax1.set_ylim(0, 1)
    ax1.legend(loc='upper right', fontsize=9)  # FIX: was lower left
    ax1.set_title('Gateway Tier Volume Shares', fontweight='bold', fontsize=11)

    # Panel B: Dual HHI
    tier_hhi_r = hhi['tier_hhi'].rolling(7, min_periods=1).mean()
    entity_hhi_r = hhi['entity_hhi'].rolling(7, min_periods=1).mean()

    ax2.plot(hhi.index, tier_hhi_r, color='#003366', linewidth=1.5,
             label='Tier-level HHI (7-day avg)')
    ax2.plot(hhi.index, entity_hhi_r, color='#d68910', linewidth=1.5,
             label='Entity-level HHI (7-day avg)')
    ax2.axhline(2500, color='#CC3333', linestyle=':', linewidth=1.2, alpha=0.7)
    ax2.text(hhi.index[10], 2700, 'DOJ/FTC Threshold (2,500)',
             fontsize=8, color='#CC3333', fontstyle='italic')
    ax2.axhline(hhi['tier_hhi'].mean(), color='#003366', linestyle='--',
                linewidth=0.8, alpha=0.5)
    ax2.axhline(hhi['entity_hhi'].mean(), color='#d68910', linestyle='--',
                linewidth=0.8, alpha=0.5)
    ax2.axvspan(pd.Timestamp('2023-03-08'), pd.Timestamp('2023-03-15'),
                color='#ffcccc', alpha=0.3)
    ax2.set_ylabel('Herfindahl-Hirschman Index')
    ax2.set_ylim(0, 10000)
    ax2.legend(loc='upper right', fontsize=9)
    ax2.set_title('Gateway Routing Concentration (HHI)', fontweight='bold', fontsize=11)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))

    fig.suptitle('Gateway Routing Concentration (Expanded Registry)',
                 fontweight='bold', fontsize=13, y=1.02)
    fig.tight_layout()

    fname = 'exhibit10_gateway_concentration_hhi_v2'
    for ext in ['.png', '.pdf']:
        fig.savefig(EXHIBITS_DIR / f'{fname}{ext}',
                    dpi=300, bbox_inches='tight', facecolor='white')
    # Copy to media locations
    for d in [MEDIA, HANDOFF_MEDIA, HANDOFF_EXHI]:
        fig.savefig(d / f'{fname}.png',
                    dpi=300, bbox_inches='tight', facecolor='white')
        print(f'  Saved: {d / fname}.png')
    plt.close(fig)
    print('  \u2714 Exhibit 17 fixed (legend upper-right)')


# ═════════════════════════════════════════════════════════════
# EXHIBIT 19: Network Topology — remove title number + fix overlap
# ═════════════════════════════════════════════════════════════
def fix_exhibit19():
    print("\n" + "=" * 60)
    print("EXHIBIT 19: Remove title number + fix Panel B overlap")
    print("=" * 60)

    # ── Data (hardcoded from paper + chart reading) ──────────
    months = pd.to_datetime([
        '2023-02', '2023-05', '2023-08', '2023-11',
        '2024-02', '2024-05', '2024-08', '2024-11',
        '2025-02', '2025-05', '2025-08', '2025-11',
    ])

    # Panel A: Market Maker Concentration
    wintermute = [1.4, 4.3, 4.6, 8.0, 3.5, 10.0, 10.8, 11.5, 12.4, 13.0, 19.9, 10.0]
    cumberland = [3.1, 2.0, 1.8, 1.5, 1.5, 1.3, 1.7, 1.6, 0.5, 0.5, 0.3, 0.1]

    # Panel B: Network Connectivity
    bridges = [8.8, 10.1, 6.9, 7.8, 8.4, 8.2, 8.5, 6.8, 6.2, 5.1, 8.9, 5.0]
    counterparties = [1090, 1090, 1050, 1080, 1050, 1020, 1060, 960, 870, 800, 780, 810]

    # ── Style ────────────────────────────────────────────────
    NAVY = '#1a2744'
    GOLD = '#d68910'
    STEEL = '#4682B4'

    plt.rcParams.update({
        'font.family': 'serif',
        'font.size': 12,
        'axes.linewidth': 0.8,
        'axes.spines.top': False,
        'axes.spines.right': True,  # need right spine for dual axis
        'figure.facecolor': 'white',
    })

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 4.5))

    # ── Panel A: Market Maker Concentration ──────────────────
    ax1.plot(months, wintermute, color=NAVY, linewidth=2.2, marker='o',
             markersize=6, label='Wintermute', zorder=5)
    ax1.plot(months, cumberland, color=GOLD, linewidth=2.2, marker='s',
             markersize=6, label='Cumberland', zorder=5)

    # Event lines
    svb_date = pd.Timestamp('2023-03-10')
    busd_date = pd.Timestamp('2023-02-13')
    ax1.axvline(svb_date, color='#CC3333', linestyle='--', linewidth=1, alpha=0.6,
                label='SVB (Mar 2023)')
    ax1.axvline(busd_date, color='#808080', linestyle=':', linewidth=1, alpha=0.6,
                label='BUSD (Feb 2023)')

    ax1.set_ylabel('Share of Total Counterparty Volume (%)')
    ax1.set_ylim(0, max(wintermute) * 1.1)
    ax1.set_title('A. Market Maker Concentration', fontweight='bold', fontsize=11)
    ax1.legend(loc='upper left', fontsize=9)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax1.grid(True, alpha=0.3)

    # ── Panel B: Network Connectivity (dual y-axes) ──────────
    ax2.plot(months, bridges, color=NAVY, linewidth=2.2, marker='o',
             markersize=6, label='Cross-gateway bridges (%)', zorder=5)
    ax2.set_ylabel('Cross-Gateway Bridge Share (%)', color=NAVY)
    ax2.tick_params(axis='y', labelcolor=NAVY)
    ax2.set_ylim(0, max(bridges) * 1.25)
    ax2.grid(True, alpha=0.3)

    # Right y-axis: unique counterparties
    ax2b = ax2.twinx()
    ax2b.plot(months, counterparties, color=STEEL, linewidth=1.8, marker='s',
              markersize=5, linestyle='--', label='Unique counterparties', zorder=4)
    ax2b.set_ylabel('Unique Counterparties', color=STEEL)
    ax2b.tick_params(axis='y', labelcolor=STEEL)
    ax2b.set_ylim(600, max(counterparties) * 1.15)
    # FIX: push right y-axis label away from data to prevent overlap
    ax2b.yaxis.set_label_coords(1.14, 0.5)

    # Event lines
    ax2.axvline(svb_date, color='#CC3333', linestyle='--', linewidth=1, alpha=0.6)
    ax2.axvline(busd_date, color='#808080', linestyle=':', linewidth=1, alpha=0.6)

    ax2.set_title('B. Network Connectivity', fontweight='bold', fontsize=11)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))

    # FIX: Combined legend placed in upper-right, below title, clear of data
    lines_a, labels_a = ax2.get_legend_handles_labels()
    lines_b, labels_b = ax2b.get_legend_handles_labels()
    ax2.legend(lines_a + lines_b, labels_a + labels_b,
               loc='upper right', fontsize=9, framealpha=0.9)

    # FIX: Title WITHOUT exhibit number prefix
    fig.suptitle('Time-Varying Gateway Network Topology',
                 fontweight='bold', fontsize=14, y=1.02)

    # Source footnote
    fig.text(0.01, -0.04,
             'Source: Nansen blockchain analytics, quarterly counterparty data for 15 gateways.',
             fontsize=9, fontstyle='italic', color='#666666')

    fig.tight_layout(rect=[0, 0, 0.97, 0.95])

    fname = 'exhibit21b_network_timeseries.png'
    for d in [MEDIA, HANDOFF_MEDIA, HANDOFF_EXHI]:
        path = d / fname
        fig.savefig(path, dpi=300, bbox_inches='tight', facecolor='white')
        print(f'  Saved: {path}')
    plt.close(fig)

    # ── Verification ─────────────────────────────────────────
    title = fig._suptitle.get_text() if fig._suptitle else ''
    print(f'\n  Title: "{title}"')
    print(f'  Contains "Exhibit 21b": {"FAIL" if "Exhibit 21b" in title else "OK - removed"}')
    print(f'  Wintermute range: {wintermute[0]}% \u2192 {max(wintermute)}% (peak)')
    print(f'  Cumberland range: {cumberland[0]}% \u2192 {cumberland[-1]}%')
    print(f'  Bridges range: {bridges[0]}% \u2192 {bridges[-1]}%')
    print(f'  Counterparties range: {counterparties[0]} \u2192 {counterparties[-1]}')
    print('  \u2714 Exhibit 19 fixed')


# ═════════════════════════════════════════════════════════════
if __name__ == '__main__':
    fix_exhibit17()
    fix_exhibit19()
    print("\n" + "=" * 60)
    print("BOTH EXHIBITS FIXED")
    print("=" * 60)
