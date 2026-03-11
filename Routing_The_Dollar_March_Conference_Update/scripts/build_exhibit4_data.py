"""Build Exhibit 4 from real data: T-Bill Rate Minus DeFi Lending Rate.

Expected inputs (drop into data/raw/):
  data/raw/dtb3_daily.csv           — columns: date, DTB3
  data/raw/aave_v3_usdc_daily.csv   — columns: date, supply_rate

Data sourcing:
  DTB3: FRED download → https://fred.stlouisfed.org/series/DTB3 → CSV
  Aave V3 USDC rate: DefiLlama yields API →
    https://yields.llama.fi/chart/aa70268e-4b52-42bf-a116-608b370f063d
    (Aave V3 Ethereum USDC pool; average hourly snapshots to daily)

Processing:
  1. Load DTB3 (daily), forward-fill weekends/holidays
  2. Load Aave V3 rate (daily)
  3. Compute spread = DTB3 - aave_rate (both in percentage points)
  4. Resample to weekly (Wednesday) to match cointegration sample
  5. Load stablecoin_supply_extended.csv, compute weekly log-difference
  6. Align on date, trim to Feb 2023 – Jan 2026 (T = 155 weeks)
  7. Verify: print mean spread, correlation, n
  8. Generate chart using exact layout from layout preview

Expected verification output:
  mean spread ~ -0.24 pp
  r(spread, growth) ~ -0.47
  n = 155
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
import sys
import warnings
warnings.filterwarnings('ignore')

# ── Paths ────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent
MEDIA = BASE / 'media'
DATA_RAW = BASE / 'data' / 'raw'
DATA_PROC = BASE / 'data' / 'processed'

HANDOFF = Path('/home/user/Claude/handoff')
HF_MEDIA = HANDOFF / 'media'
HF_EXHI = HANDOFF / 'exhibits'
for d in [MEDIA, HF_MEDIA, HF_EXHI, DATA_PROC]:
    d.mkdir(parents=True, exist_ok=True)

# ── Colors ───────────────────────────────────────────────────
NAVY = '#003366'
RED = '#CC3333'
GREEN = '#339933'


def save_all(fig, name):
    for d in [MEDIA, HF_MEDIA, HF_EXHI]:
        fig.savefig(d / name, dpi=300, bbox_inches='tight', facecolor='white')
        print(f'  Saved: {d / name}')
    plt.close(fig)


def load_dtb3():
    """Load 3-month T-bill rate from FRED CSV."""
    path = DATA_RAW / 'dtb3_daily.csv'
    if not path.exists():
        print(f"  ERROR: {path} not found.")
        print(f"  Download from: https://fred.stlouisfed.org/series/DTB3")
        print(f"  Save as CSV with columns: date, DTB3")
        return None

    df = pd.read_csv(path)
    # Handle various FRED CSV formats
    if 'DATE' in df.columns:
        df = df.rename(columns={'DATE': 'date'})
    if 'date' not in df.columns:
        df.columns = ['date', 'DTB3']

    # Find the rate column (DTB3 or second column)
    rate_col = 'DTB3' if 'DTB3' in df.columns else df.columns[1]
    df['date'] = pd.to_datetime(df['date'])
    df['DTB3'] = pd.to_numeric(df[rate_col], errors='coerce')
    df = df[['date', 'DTB3']].set_index('date').sort_index()
    df['DTB3'] = df['DTB3'].ffill()  # forward-fill weekends/holidays
    print(f"  DTB3: {len(df)} daily obs, {df.index[0].date()} to {df.index[-1].date()}")
    return df


def load_aave_rate():
    """Load Aave V3 USDC supply rate from DefiLlama CSV."""
    path = DATA_RAW / 'aave_v3_usdc_daily.csv'
    if not path.exists():
        print(f"  ERROR: {path} not found.")
        print(f"  Source: DefiLlama yields API")
        print(f"  Pool ID: aa70268e-4b52-42bf-a116-608b370f063d")
        print(f"  URL: https://yields.llama.fi/chart/aa70268e-4b52-42bf-a116-608b370f063d")
        print(f"  Save as CSV with columns: date, supply_rate")
        return None

    df = pd.read_csv(path)
    if 'date' not in df.columns:
        df.columns = ['date', 'supply_rate']

    rate_col = 'supply_rate' if 'supply_rate' in df.columns else (
        'apy' if 'apy' in df.columns else df.columns[1])
    df['date'] = pd.to_datetime(df['date'])
    df['aave_rate'] = pd.to_numeric(df[rate_col], errors='coerce')
    df = df[['date', 'aave_rate']].set_index('date').sort_index()
    print(f"  Aave V3 USDC: {len(df)} daily obs, {df.index[0].date()} to {df.index[-1].date()}")
    return df


def load_supply_growth():
    """Load stablecoin supply and compute weekly log-difference growth."""
    path = DATA_RAW / 'stablecoin_supply_extended.csv'
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    supply = df['total_supply'].dropna()
    weekly = supply.resample('W-WED').last().dropna()
    weekly = weekly['2023-02-01':'2026-01-31']
    growth = np.log(weekly).diff() * 100  # percent log-diff
    growth = growth.dropna()
    print(f"  Supply growth: {len(growth)} weekly obs")
    return growth


def generate_chart(spread_weekly, growth, output_name='exhibit13_yield_spread.png'):
    """Generate the dual-axis chart. Layout matches the approved preview."""
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
    ax1.plot(spread_weekly.index, spread_weekly.values,
             color=NAVY, linewidth=1.5, label='T-bill minus Aave V3 USDC rate (left)')
    ax1.fill_between(spread_weekly.index, spread_weekly.values, 0,
                     where=spread_weekly.values < 0,
                     color=RED, alpha=0.15, interpolate=True)
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

    # X-axis formatting — quarterly ticks with rotation to prevent cramping
    ax1.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    fig.autofmt_xdate(rotation=45, ha='right')

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2,
               loc='upper right', fontsize=9, frameon=False)

    # Source footnote
    fig.text(0.02, 0.01,
             "Source: Author's calculations using FRED (DTB3) and DefiLlama (Aave V3 USDC rate) data.",
             fontsize=8, fontstyle='italic', color='#666666')

    fig.tight_layout()
    save_all(fig, output_name)


def main():
    print("=" * 60)
    print("EXHIBIT 4: T-Bill Rate Minus DeFi Lending Rate (Real Data)")
    print("=" * 60)

    # Load inputs
    dtb3 = load_dtb3()
    aave = load_aave_rate()
    growth = load_supply_growth()

    if dtb3 is None or aave is None:
        print("\n  MISSING INPUT DATA. Cannot generate from real data.")
        print("  Required files:")
        print("    data/raw/dtb3_daily.csv          (FRED series DTB3)")
        print("    data/raw/aave_v3_usdc_daily.csv  (DefiLlama Aave V3 USDC pool)")
        print("\n  To get DTB3:")
        print("    https://fred.stlouisfed.org/series/DTB3 -> Download CSV")
        print("\n  To get Aave V3 USDC rate:")
        print("    https://yields.llama.fi/chart/aa70268e-4b52-42bf-a116-608b370f063d")
        print("    Or use DefiLlama API to pull daily yield snapshots.")
        sys.exit(1)

    # Expand DTB3 to daily calendar frequency (fill weekends/holidays)
    dtb3 = dtb3.asfreq('D').ffill()

    # Compute daily spread
    spread_daily = dtb3['DTB3'] - aave['aave_rate']
    spread_daily = spread_daily.dropna()
    print(f"  Daily spread: {len(spread_daily)} obs, "
          f"mean={spread_daily.mean():.2f} pp")

    # Resample to weekly (Wednesday) to match cointegration sample
    spread_weekly = spread_daily.resample('W-WED').last()
    spread_weekly = spread_weekly['2023-02-01':'2026-01-31'].dropna()

    # Align with growth on shared dates
    aligned = pd.DataFrame({
        'spread': spread_weekly,
        'growth': growth
    }).dropna()

    # Trim to 155 weeks
    aligned = aligned.iloc[:155]
    n = len(aligned)

    # Verification
    mean_spread = aligned['spread'].mean()
    r = np.corrcoef(aligned['spread'].values, aligned['growth'].values)[0, 1]
    print(f"\n  VERIFICATION:")
    print(f"    n = {n} weeks (paper: 155)")
    print(f"    Mean spread = {mean_spread:.2f} pp (paper: -0.24)")
    print(f"    r(spread, growth) = {r:.2f} (paper: -0.47)")

    if abs(n - 155) > 5:
        print(f"  WARNING: Sample size {n} differs substantially from paper's 155.")
    if abs(mean_spread - (-0.24)) > 0.5:
        print(f"  WARNING: Mean spread {mean_spread:.2f} differs from paper's -0.24.")
    if abs(r - (-0.47)) > 0.15:
        print(f"  WARNING: Correlation {r:.2f} differs from paper's -0.47.")

    # Save processed data
    aligned.to_csv(DATA_PROC / 'exhibit4_spread_growth.csv')
    print(f"  Saved: {DATA_PROC / 'exhibit4_spread_growth.csv'}")

    # Decide output filename based on verification
    mean_ok = abs(mean_spread - (-0.24)) < 0.1
    r_ok = abs(r - (-0.47)) < 0.1
    status = "PASS" if mean_ok and r_ok else "CHECK"

    print(f"\n  === EXHIBIT 4 VERIFICATION ===")
    print(f"  Data source: FRED DTB3 + DefiLlama Aave V3 USDC rate (REAL DATA)")
    print(f"  n = {n} weeks")
    print(f"  Mean spread = {mean_spread:.2f} pp (target: -0.24)")
    print(f"  r(spread, growth) = {r:.2f} (target: -0.47)")

    if status == "PASS":
        generate_chart(aligned['spread'], aligned['growth'],
                       output_name='exhibit13_yield_spread.png')
        print(f"  STATUS: PASS")
        print(f"  Exhibit 4 generated from REAL data.")
    else:
        generate_chart(aligned['spread'], aligned['growth'],
                       output_name='exhibit13_yield_spread_REVIEW.png')
        print(f"  STATUS: CHECK — stats diverge from paper")
        print(f"  Saved as _REVIEW.png — NOT overwriting production exhibit.")
        print(f"  Investigate: resampling method, rate column (apyBase vs apy), date alignment.")


if __name__ == '__main__':
    main()
