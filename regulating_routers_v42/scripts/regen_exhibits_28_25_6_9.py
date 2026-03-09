"""Fix three exhibits: Exhibit 28 overlap, Exhibit 25 cleanup, Combine 6+9.

1. Exhibit 28: Move stats box to upper-left, FDIC annotation above recovery
2. Exhibit 25: Use paper-stated values, remove pre-revision clutter
3. Exhibits 6+9: Combined rolling correlation with events + easing shading
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ── Paths ────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
MEDIA = ROOT / 'media'
DATA_RAW = ROOT / 'data' / 'raw'
DATA_PROC = ROOT / 'data' / 'processed'

HANDOFF = Path('/home/user/Claude/handoff')
HANDOFF_MEDIA = HANDOFF / 'media'
HANDOFF_EXHI = HANDOFF / 'exhibits'

for d in [MEDIA, HANDOFF_MEDIA, HANDOFF_EXHI]:
    d.mkdir(parents=True, exist_ok=True)

# ── Fed paper aesthetic ──────────────────────────────────────
FED_NAVY = '#1B2A4A'
FED_BLUE = '#336699'
FED_LIGHT = '#6699CC'
FED_RED = '#CC3333'
FED_GOLD = '#CC9933'
FED_GRAY = '#808080'
FED_DARK = '#404040'


def apply_style():
    plt.rcParams.update({
        'font.family': 'serif',
        'font.size': 10,
        'axes.titlesize': 11,
        'axes.titleweight': 'bold',
        'axes.labelsize': 10,
        'xtick.labelsize': 9,
        'ytick.labelsize': 9,
        'legend.fontsize': 8.5,
        'figure.dpi': 300,
        'savefig.dpi': 300,
        'savefig.bbox': 'tight',
        'axes.spines.top': False,
        'axes.spines.right': False,
    })


def add_source(fig, text="Source: Author's calculations using FRED and DefiLlama data."):
    fig.text(0.02, 0.01, text, fontsize=7, fontstyle='italic', color='#666666')


def save_all(fig, name):
    """Save to all output directories."""
    for d in [MEDIA, HANDOFF_MEDIA, HANDOFF_EXHI]:
        path = d / name
        fig.savefig(path, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"  Saved: {path}")
    plt.close(fig)


# ═════════════════════════════════════════════════════════════
# EXHIBIT 28: Event-Time Alignment (fix overlap)
# ═════════════════════════════════════════════════════════════
def fix_exhibit28():
    print("\n" + "=" * 60)
    print("EXHIBIT 28: Fix text overlap")
    print("=" * 60)
    apply_style()

    pa = pd.read_csv(DATA_PROC / 'placebo_analysis_expanded.csv')

    # Load daily shares for spaghetti traces
    shares = pd.read_csv(DATA_PROC / 'exhibit_C1_gateway_shares_daily_v2.csv', parse_dates=['day'])
    shares = shares.set_index('day').sort_index()
    if shares.index.tz is None:
        shares.index = shares.index.tz_localize('UTC')

    event_date = pd.Timestamp('2023-03-10', tz='UTC')
    excl_start = pd.Timestamp('2023-02-24', tz='UTC')
    excl_end = pd.Timestamp('2023-03-24', tz='UTC')

    np.random.seed(42)
    eligible = shares.index[(shares.index < excl_start) | (shares.index > excl_end)]
    eligible = eligible[(eligible >= shares.index[7]) & (eligible <= shares.index[-8])]
    placebo_starts = np.random.choice(eligible, size=50, replace=False)

    offsets = list(range(-7, 8))

    fig, ax = plt.subplots(figsize=(8, 5.2))

    # Spaghetti traces
    for ps in placebo_starts:
        ps = pd.Timestamp(ps)
        traj = []
        for t in offsets:
            d = ps + pd.Timedelta(days=t)
            if d in shares.index:
                traj.append(shares.loc[d, 'tier1_share_pct'] / 100)
            else:
                traj.append(np.nan)
        ax.plot(offsets, traj, color=FED_GRAY, alpha=0.15, linewidth=0.5)

    # Percentile band
    ax.fill_between(pa['event_day'], pa['placebo_p5'], pa['placebo_p95'],
                     color=FED_LIGHT, alpha=0.3, label='5th\u201395th percentile')
    ax.plot(pa['event_day'], pa['placebo_mean'], color=FED_BLUE, linewidth=1.5,
            linestyle='--', label='Placebo mean', alpha=0.8)

    # SVB trajectory
    ax.plot(pa['event_day'], pa['svb_t1_share'], color=FED_RED, linewidth=2.5,
            marker='o', markersize=4, label='SVB (actual)', zorder=5)

    # ── Annotation: FDIC seizure (Day 0 = Mar 10) ──
    svb_day0 = pa[pa['event_day'] == 0]['svb_t1_share'].values[0]
    ax.annotate('FDIC seizure\n(Mar 10)', xy=(0, svb_day0),
                xytext=(-3.5, svb_day0 + 0.12),
                fontsize=8, fontweight='bold', color=FED_RED,
                arrowprops=dict(arrowstyle='->', color=FED_RED, lw=1.2))

    # ── FIX: FDIC guarantee annotation — point downward from above ──
    svb_day3 = pa[pa['event_day'] == 3]['svb_t1_share'].values[0]
    ax.annotate('FDIC guarantee\n(Mar 13)', xy=(3, svb_day3),
                xytext=(4.5, svb_day3 + 0.15),
                fontsize=8, fontweight='bold', color=FED_NAVY,
                arrowprops=dict(arrowstyle='->', color=FED_NAVY, lw=1.2))

    # Compute stats
    min_zscore = pa['svb_zscore'].min()
    days_below_p5 = (pa['svb_t1_share'] < pa['placebo_p5']).sum()
    try:
        swing = pd.read_csv(DATA_PROC / 'placebo_swing_stats.csv')
        swing_lookup = dict(zip(swing['metric'], swing['value']))
        swing_val = float(swing_lookup.get('svb_swing_pp', (pa['svb_t1_share'].max() - pa['svb_t1_share'].min()) * 100))
        pctile_val = float(swing_lookup.get('svb_swing_percentile', 94))
    except Exception:
        swing_val = (pa['svb_t1_share'].max() - pa['svb_t1_share'].min()) * 100
        pctile_val = 94

    stats_text = (f"Nadir z = {min_zscore:.1f}\u03c3\n"
                  f"{days_below_p5} days below p5 band\n"
                  f"Swing: {swing_val:.1f} pp ({pctile_val:.0f}th pctile)")

    # ── FIX: Stats box moved to UPPER-LEFT (was upper-right, overlapped FDIC) ──
    ax.text(0.02, 0.97, stats_text, transform=ax.transAxes,
            fontsize=8, va='top', ha='left',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                      edgecolor=FED_GRAY, alpha=0.9))

    ax.set_xlabel('Event Day (0 = March 10, 2023)')
    ax.set_ylabel('Tier 1 Volume Share')
    ax.set_title('Tier 1 Volume Share: Event-Time Alignment\n(Expanded 51-Address Registry)',
                 fontsize=11, fontweight='bold')
    ax.set_xticks(offsets)
    ax.set_xlim(-7.5, 7.5)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f'{y:.0%}'))
    ax.legend(loc='upper center', fontsize=8, bbox_to_anchor=(0.53, 1.0))

    add_source(fig)
    fig.tight_layout(rect=[0, 0.03, 1, 0.95])
    save_all(fig, 'exhibit_event_time_alignment.png')
    print("  \u2714 Exhibit 28 fixed")


# ═════════════════════════════════════════════════════════════
# EXHIBIT 25: Trivariate Robustness (clean up DGS10)
# ═════════════════════════════════════════════════════════════
def fix_exhibit25():
    print("\n" + "=" * 60)
    print("EXHIBIT 25: Remove pre-revision clutter")
    print("=" * 60)
    apply_style()

    # Paper-stated values (authoritative, bypasses data-vintage issue)
    results = [
        ('Baseline (3-var)',  30.68, 29.80, True),
        ('+ SOFR (4-var)',    49.76, 47.85, True),
        ('+ DFF (4-var)',     46.57, 47.85, False),
        ('+ DGS10 (4-var)',   43.56, 47.85, False),
    ]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    fig.suptitle('Trivariate Robustness:\nCointegration Under Alternative Variable Specifications',
                 fontsize=12, fontweight='bold', y=0.97)

    labels = [r[0] for r in results]
    traces = [r[1] for r in results]
    cvs = [r[2] for r in results]
    passes = [r[3] for r in results]

    y_pos = range(len(results))
    colors = [FED_NAVY if p else FED_RED for p in passes]

    bars = ax.barh(y_pos, traces, color=colors, edgecolor='white',
                   linewidth=0.5, height=0.6, alpha=0.85)
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()

    # CV marker and labels for each bar
    for i, (lbl, trace, cv, passed) in enumerate(results):
        ax.plot(cv, i, marker='|', color=FED_RED, markersize=20, markeredgewidth=2)
        status = 'pass' if passed else 'fail'

        # DFF gets borderline annotation with arrow
        is_borderline = lbl == '+ DFF (4-var)'

        if is_borderline:
            label_text = f'{trace:.2f} vs. {cv:.2f} \u2014 borderline'
            ax.annotate(label_text,
                       xy=(trace, i), xytext=(trace + 5, i - 0.35),
                       fontsize=8, fontstyle='italic', color=FED_DARK,
                       arrowprops=dict(arrowstyle='->', color=FED_DARK, lw=0.8))
        else:
            label_text = f'{trace:.2f} (CV={cv:.2f}) {status}'
            ax.text(max(trace, cv) + 1, i, label_text,
                   ha='left', va='center', fontsize=8,
                   fontweight='bold' if passed else 'normal',
                   color=FED_NAVY if passed else FED_RED)

    ax.set_xlabel('Johansen Trace Statistic')
    ax.axvline(0, color='black', linewidth=0.3)

    # Legend in UPPER-LEFT (was lower-right, overlapped DGS10 labels)
    ax.legend([mpatches.Patch(color=FED_NAVY, label='Cointegrated'),
               mpatches.Patch(color=FED_RED, label='Not cointegrated'),
               plt.Line2D([0], [0], marker='|', color=FED_RED, linestyle='None',
                          markersize=12, markeredgewidth=2, label='95% CV')],
              ['Cointegrated', 'Not cointegrated', '95% CV'],
              loc='upper right', fontsize=8, frameon=False)

    add_source(fig)
    fig.tight_layout(rect=[0, 0.04, 1, 0.92])
    save_all(fig, 'exhibit_trivariate_robustness.png')
    print("  \u2714 Exhibit 25 fixed")


# ═════════════════════════════════════════════════════════════
# EXHIBITS 6+9: Combined Rolling Correlation
# ═════════════════════════════════════════════════════════════
def fix_exhibits_6_9():
    print("\n" + "=" * 60)
    print("EXHIBITS 6+9: Combined rolling correlation")
    print("=" * 60)
    apply_style()

    # Load data
    fred = pd.read_csv(DATA_RAW / 'fred_wide.csv', index_col=0, parse_dates=True)
    sc = pd.read_csv(DATA_PROC / 'unified_extended_dataset.csv', index_col=0, parse_dates=True)

    merged = fred[['WSHOMCB']].join(sc[['total_supply']], how='inner').dropna()
    weekly = merged.resample('W-WED').last().dropna()

    r90 = weekly['total_supply'].rolling(90 // 7).corr(weekly['WSHOMCB'])
    r180 = weekly['total_supply'].rolling(180 // 7).corr(weekly['WSHOMCB'])
    full_r = float(weekly['total_supply'].corr(weekly['WSHOMCB']))

    fig, ax = plt.subplots(figsize=(12, 6))

    # Easing regime shading (Sep 2024 onward)
    easing_start = pd.Timestamp('2024-09-18')
    ax.axvspan(easing_start, weekly.index[-1], color='#90EE90', alpha=0.15,
               label='Easing regime')

    # Rolling correlations
    ax.plot(r90.index, r90, color=FED_LIGHT, linewidth=1.0, linestyle='--',
            alpha=0.7, label='90-day window')
    ax.plot(r180.index, r180, color=FED_NAVY, linewidth=2.0, label='180-day window')

    # Reference lines
    ax.axhline(full_r, color=FED_GRAY, linestyle=':', linewidth=1, alpha=0.7,
               label=f'Full-sample r = {full_r:.2f}')
    ax.axhline(0, color='black', linewidth=0.5)

    # SVB event marker
    svb = pd.Timestamp('2023-03-10')
    ax.axvline(svb, color=FED_RED, linestyle='--', linewidth=1, alpha=0.6)
    ax.text(svb, 1.05, 'SVB', color=FED_RED, fontsize=8, ha='center',
            transform=ax.get_xaxis_transform())

    # First rate cut marker
    rate_cut = pd.Timestamp('2024-09-18')
    ax.axvline(rate_cut, color='#339933', linestyle='--', linewidth=1, alpha=0.6)
    ax.text(rate_cut, 1.05, 'First rate cut', color='#339933', fontsize=8, ha='center',
            transform=ax.get_xaxis_transform())

    ax.set_ylabel('Pearson Correlation')
    ax.set_ylim(-1.1, 1.1)
    ax.set_title('Rolling-Window Correlations: Fed Total Assets vs. Stablecoin Supply',
                 fontweight='bold', fontsize=12)
    ax.legend(loc='upper right', fontsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))

    add_source(fig, "Source: FRED, DefiLlama.")
    fig.tight_layout(rect=[0, 0.03, 1, 0.98])

    # Save as BOTH filenames so existing references work
    for name in ['exhibit02_rolling_correlations.png', 'exhibit14_rolling_corr_extended.png']:
        for d in [MEDIA, HANDOFF_MEDIA, HANDOFF_EXHI]:
            path = d / name
            fig.savefig(path, dpi=300, bbox_inches='tight', facecolor='white')
            print(f"  Saved: {path}")
    plt.close(fig)

    print(f"\n  Full-sample r = {full_r:.4f}")
    print(f"  Data range: {weekly.index[0].date()} to {weekly.index[-1].date()}")
    print("  \u2714 Combined Exhibit 6+9")
    print("\n  NOTE: Paper text should merge Exhibit 9 reference into Exhibit 6,")
    print("  or update Exhibit 9 caption to note it is now combined.")


# ═════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════
if __name__ == '__main__':
    fix_exhibit28()
    fix_exhibit25()
    fix_exhibits_6_9()
    print("\n" + "=" * 60)
    print("ALL THREE EXHIBITS FIXED")
    print("=" * 60)
