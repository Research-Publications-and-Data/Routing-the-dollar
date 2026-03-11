"""Fix Exhibit 4: Replace wrong chart (old yield-curve spread) with correct
T-bill minus DeFi lending rate vs. stablecoin supply growth.

Data situation:
  - DTB3 (3-month T-bill) and Aave V3 USDC rate are NOT in the repo.
  - Stablecoin supply IS available (data/raw/stablecoin_supply_extended.csv).
  - Paper states: spread mean = -0.24 pp, r(spread, growth) = -0.47, n = 155 weeks.

Approach: Use real supply data for growth; synthesize spread to match known moments.
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
DATA_RAW = BASE / 'data' / 'raw'

HANDOFF = Path('/home/user/Claude/handoff')
HF_MEDIA = HANDOFF / 'media'
HF_EXHI = HANDOFF / 'exhibits'
for d in [MEDIA, HF_MEDIA, HF_EXHI]:
    d.mkdir(parents=True, exist_ok=True)

# ── Colors ───────────────────────────────────────────────────
NAVY = '#003366'
RED = '#CC3333'
LIGHT_RED = '#CC3333'
GREEN = '#339933'


def save_all(fig, name):
    for d in [MEDIA, HF_MEDIA, HF_EXHI]:
        fig.savefig(d / name, dpi=300, bbox_inches='tight', facecolor='white')
        print(f'  Saved: {d / name}')
    plt.close(fig)


def main():
    print("=" * 60)
    print("EXHIBIT 4: T-Bill Rate Minus DeFi Lending Rate")
    print("=" * 60)

    # ── Load real stablecoin supply ──────────────────────────
    supply_raw = pd.read_csv(DATA_RAW / 'stablecoin_supply_extended.csv',
                             index_col=0, parse_dates=True)
    supply_daily = supply_raw['total_supply'].dropna()

    # Resample to weekly (Wed), compute log-difference growth
    supply_weekly = supply_daily.resample('W-WED').last().dropna()
    supply_weekly = supply_weekly['2023-02-01':'2026-01-31']
    growth = np.log(supply_weekly).diff() * 100  # percent log-diff
    growth = growth.dropna()

    # Trim to n=155 weeks (paper's stated sample)
    growth = growth.iloc[:155]
    n = len(growth)
    print(f"  Supply growth: {n} weeks, mean={growth.mean():.4f}%, std={growth.std():.4f}%")

    # ── Synthesize spread to match paper moments ─────────────
    # Known: spread mean = -0.24 pp, r(spread, growth) = -0.47
    # Method: construct spread = a + b * growth + noise, calibrated to moments
    np.random.seed(2023)
    target_r = -0.47
    target_mean = -0.24
    spread_std = 1.8  # reasonable for T-bill minus DeFi spread

    # Standardize growth
    g_std = (growth.values - growth.mean()) / growth.std()

    # Correlated component + independent noise
    # spread = target_mean + spread_std * (target_r * g_std + sqrt(1-r^2) * noise)
    noise = np.random.normal(0, 1, n)
    raw_spread = target_r * g_std + np.sqrt(1 - target_r**2) * noise
    spread = target_mean + spread_std * raw_spread

    # Add some autocorrelation for realism (smooth with EMA)
    spread_series = pd.Series(spread, index=growth.index)
    spread_series = spread_series.ewm(span=4).mean()

    # Re-center to target mean after smoothing
    spread_series = spread_series - spread_series.mean() + target_mean

    actual_r = np.corrcoef(spread_series.values, growth.values)[0, 1]
    print(f"  Spread: mean={spread_series.mean():.2f} pp, std={spread_series.std():.2f}")
    print(f"  Correlation(spread, growth): r = {actual_r:.2f} (target: {target_r})")

    # ── Plot ─────────────────────────────────────────────────
    plt.rcParams.update({
        'font.family': 'serif',
        'font.size': 10,
        'axes.titlesize': 13,
        'axes.titleweight': 'bold',
        'axes.labelsize': 11,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10,
        'legend.fontsize': 9,
        'figure.dpi': 300,
        'savefig.dpi': 300,
        'axes.spines.top': False,
    })

    fig, ax1 = plt.subplots(figsize=(10, 5))

    # Left axis: yield spread
    ax1.plot(spread_series.index, spread_series.values,
             color=NAVY, linewidth=1.5, label='T-bill minus Aave V3 USDC rate (left)')
    ax1.fill_between(spread_series.index, spread_series.values, 0,
                     where=spread_series.values < 0,
                     color=LIGHT_RED, alpha=0.15, interpolate=True)
    ax1.axhline(0, color='gray', linewidth=0.5)
    ax1.set_ylabel('Yield Spread (pp)', color=NAVY, fontsize=11)
    ax1.tick_params(axis='y', labelcolor=NAVY)

    # Right axis: supply growth
    ax2 = ax1.twinx()
    ax2.plot(growth.index, growth.values,
             color=RED, linewidth=1.2, linestyle='--', alpha=0.8,
             label='Stablecoin supply growth (right)')
    ax2.set_ylabel('Weekly Supply Growth (%)', color=RED, fontsize=11)
    ax2.tick_params(axis='y', labelcolor=RED)
    ax2.spines['top'].set_visible(False)

    # Event markers
    # SVB stress band
    ax1.axvspan(pd.Timestamp('2023-03-08'), pd.Timestamp('2023-03-15'),
                alpha=0.12, color=RED, zorder=0)
    ax1.annotate('SVB', xy=(pd.Timestamp('2023-03-11'), ax1.get_ylim()[1] * 0.85),
                 fontsize=8, color=RED, ha='center', fontweight='bold')

    # Sep 2024 rate cut
    ax1.axvline(pd.Timestamp('2024-09-18'), color=GREEN, linewidth=1,
                linestyle='--', alpha=0.7)
    ax1.annotate('Rate cut', xy=(pd.Timestamp('2024-09-18'), ax1.get_ylim()[1] * 0.85),
                 fontsize=8, color=GREEN, ha='left', fontweight='bold',
                 xytext=(pd.Timestamp('2024-09-25'), ax1.get_ylim()[1] * 0.85))

    # Title — NO exhibit number
    ax1.set_title('Yield Spread: T-Bill Rate Minus DeFi Lending Rate')

    # X-axis formatting
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2,
               loc='upper right', fontsize=9, frameon=False)

    # Watermark — this is synthetic data
    fig.text(0.5, 0.5, 'LAYOUT PREVIEW\nSynthetic spread data\nAwaiting DTB3 + Aave V3 inputs',
             ha='center', va='center', fontsize=20, color='red', alpha=0.25,
             fontweight='bold', rotation=30, transform=fig.transFigure)

    # Source footnote
    fig.text(0.02, 0.01,
             "LAYOUT ONLY — synthetic spread. Replace with FRED DTB3 + DefiLlama Aave V3 USDC rate.",
             fontsize=8, fontstyle='italic', color='#CC3333')

    fig.tight_layout()
    save_all(fig, 'exhibit13_yield_spread_LAYOUT_ONLY.png')

    # Verification
    print(f"\n  Verification:")
    print(f"    Title: 'Yield Spread: T-Bill Rate Minus DeFi Lending Rate' (no exhibit number)")
    print(f"    Spread mean: {spread_series.mean():.2f} pp (paper: -0.24)")
    print(f"    Correlation: {actual_r:.2f} (paper: -0.47)")
    print(f"    Weeks: {n} (paper: 155)")
    print(f"    Negative-spread shading: visible")
    print(f"    SVB marker: Mar 2023")
    print(f"    Rate cut marker: Sep 2024")


if __name__ == '__main__':
    main()
