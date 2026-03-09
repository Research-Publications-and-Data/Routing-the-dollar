"""Fix Exhibit 10: Remove 'Exhibit 16:' prefix from use-case decomposition chart.
Reads data/processed/usecase_decomposition.csv, creates stacked area chart.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ── Paths ────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent
MEDIA = BASE / 'media'
DATA_PROC = BASE / 'data' / 'processed'

HANDOFF = Path('/home/user/Claude/handoff')
HF_MEDIA = HANDOFF / 'media'
HF_EXHI = HANDOFF / 'exhibits'
for d in [MEDIA, HF_MEDIA, HF_EXHI]:
    d.mkdir(parents=True, exist_ok=True)

# ── Colors (match existing chart) ────────────────────────────
# From visual inspection of the current image:
#   Total All Chains  = dark navy (outermost)
#   Total Category Chains = steel blue
#   Defi = green
#   Cex = coral/red
#   Bridge = gray
#   Payments = gold
#   Other Cat Chains = dark slate
#   P2P All Chains = light blue (innermost)
FED_NAVY = '#1B2A4A'
STEEL_BLUE = '#4682B4'
GREEN = '#5D9B5D'
CORAL = '#CC6666'
GRAY = '#A0A0A0'
FED_GOLD = '#C5A258'
DARK_SLATE = '#2F4F4F'
LIGHT_BLUE = '#6699CC'


def save_all(fig, name):
    for d in [MEDIA, HF_MEDIA, HF_EXHI]:
        fig.savefig(d / name, dpi=200, bbox_inches='tight', facecolor='white')
        print(f'  Saved: {d / name}')
    plt.close(fig)


def main():
    print("=" * 60)
    print("EXHIBIT 10: Use-Case Decomposition (remove 'Exhibit 16:' prefix)")
    print("=" * 60)

    df = pd.read_csv(DATA_PROC / 'usecase_decomposition.csv')
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date').sort_index()

    # Forward-fill then zero-fill NaN
    df = df.ffill().fillna(0)

    # Stacking order (bottom to top) — match original image
    # The original stacks from bottom: P2P, Other Cat, Payments, Bridge, Cex, Defi,
    # Total Category Chains, Total All Chains
    stack_cols = [
        ('p2p_all_chains_B', 'P2P All Chains', LIGHT_BLUE),
        ('other_cat_chains_B', 'Other Cat Chains', DARK_SLATE),
        ('payments_B', 'Payments', FED_GOLD),
        ('bridge_B', 'Bridge', GRAY),
        ('cex_B', 'Cex', CORAL),
        ('defi_B', 'Defi', GREEN),
        ('total_category_chains_B', 'Total Category Chains', STEEL_BLUE),
        ('total_all_chains_B', 'Total All Chains', FED_NAVY),
    ]

    # Only include columns that exist and have data
    valid = [(col, label, c) for col, label, c in stack_cols if col in df.columns]

    plt.rcParams.update({
        'font.family': 'serif',
        'font.size': 10,
        'axes.titlesize': 14,
        'axes.titleweight': 'bold',
        'axes.labelsize': 11,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10,
        'legend.fontsize': 9,
        'figure.dpi': 200,
        'savefig.dpi': 200,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'axes.grid': True,
        'grid.alpha': 0.3,
    })

    fig, ax = plt.subplots(figsize=(14, 6))

    cols = [v[0] for v in valid]
    labels = [v[1] for v in valid]
    colors = [v[2] for v in valid]

    ax.stackplot(df.index, *[df[c].values for c in cols],
                 labels=labels, colors=colors, alpha=0.85)

    # Title: NO exhibit number prefix
    ax.set_title('Stablecoin Use-Case Decomposition', fontsize=14, fontweight='bold')
    ax.set_ylabel('Volume ($B)', fontsize=11)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax.get_xticklabels(), rotation=0, ha='center')

    # Legend in upper-left matching current placement
    ax.legend(loc='upper left', fontsize=9, ncol=2, frameon=False)

    # Source footnote
    fig.text(0.02, 0.01,
             "Source: Artemis.xyz, DefiLlama, authors' categorization.",
             fontsize=8, fontstyle='italic', color='#666666')

    fig.tight_layout()
    save_all(fig, 'exhibit16_usecase_decomposition.png')

    # Verify
    print(f'  Data range: {df.index[0].date()} to {df.index[-1].date()}')
    print(f'  Months: {len(df)}')
    print(f'  Columns stacked: {len(valid)}')
    print('  Title: "Stablecoin Use-Case Decomposition" (no exhibit prefix)')
    print('  \u2714 Exhibit 10 fixed')


if __name__ == '__main__':
    main()
