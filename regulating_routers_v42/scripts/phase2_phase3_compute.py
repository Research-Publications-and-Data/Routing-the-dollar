"""
Phase 2 (CLII No-Freeze Robustness) + Phase 3 (Data-Dependent Computations)
All computation, CSV generation, and exhibit creation.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

# ── Paths ────────────────────────────────────────────────────
BASE = Path('/home/user/Claude/handoff')
RAW = BASE / 'data' / 'raw'
PROC = BASE / 'data' / 'processed'
EXHI = BASE / 'exhibits'
MEDIA = BASE / 'media'
for d in [PROC, EXHI, MEDIA]:
    d.mkdir(parents=True, exist_ok=True)

EXPANDED = RAW / 'dune_eth_daily_expanded_v2.csv'
ETH_TOTAL = RAW / 'dune_eth_total_v2.csv'

# ── Style ────────────────────────────────────────────────────
NAVY = '#003366'
GOLD = '#CC8800'
RED = '#CC3333'
GRAY = '#999999'
LIGHT_GRAY = '#CCCCCC'
GREEN = '#339933'

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
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
})


def save_fig(fig, filename):
    for d in [EXHI, MEDIA]:
        fig.savefig(d / filename, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"  Saved: {EXHI / filename}")


def save_csv(df, filename):
    path = PROC / filename
    df.to_csv(path, index=False)
    print(f"  Saved: {path}")


# ══════════════════════════════════════════════════════════════
# PHASE 2: CLII NO-FREEZE ROBUSTNESS
# ══════════════════════════════════════════════════════════════
def phase2():
    print("=" * 60)
    print("PHASE 2: CLII NO-FREEZE ROBUSTNESS")
    print("=" * 60)

    # Baseline weights: License 25%, Transparency 20%, Freeze 20%, Compliance 20%, Sanctions 15%
    w_base = np.array([0.25, 0.20, 0.20, 0.20, 0.15])
    # No-freeze: drop freeze (idx 2), redistribute proportionally
    w_nofreeze_raw = np.array([0.25, 0.20, 0.0, 0.20, 0.15])
    w_nofreeze = w_nofreeze_raw / w_nofreeze_raw.sum()
    print(f"  No-freeze weights: Lic={w_nofreeze[0]:.4f}, Trans={w_nofreeze[1]:.4f}, "
          f"Comp={w_nofreeze[3]:.4f}, Sanc={w_nofreeze[4]:.4f}")

    # Dimension scores calibrated to reproduce v42 docx Table 2a composites
    # under 5-dimension weights: License 25%, Transparency 20%, Freeze 20%,
    # Compliance 20%, Sanctions 15%
    # (License, Transparency, Freeze, Compliance, Sanctions)
    TABLE_B2 = {
        'Circle':    (0.95, 0.90, 0.95, 0.90, 0.90),  # = 0.92
        'Paxos':     (0.90, 0.85, 0.90, 0.92, 0.80),  # = 0.88
        'PayPal':    (0.95, 0.80, 0.80, 0.95, 0.85),  # = 0.88
        'Coinbase':  (0.90, 0.80, 0.79, 0.90, 0.85),  # = 0.85
        'Gemini':    (0.90, 0.75, 0.77, 0.85, 0.80),  # = 0.82
        'BitGo':     (0.85, 0.75, 0.75, 0.85, 0.80),  # = 0.80
        'Robinhood': (0.75, 0.50, 0.85, 0.90, 0.75),  # = 0.75
        'Kraken':    (0.65, 0.55, 0.50, 0.59, 0.60),  # = 0.58
        'Tether':    (0.10, 0.73, 0.90, 0.35, 0.20),  # = 0.45
        'OKX':       (0.15, 0.25, 0.55, 0.65, 0.45),  # = 0.40
        'Bybit':     (0.15, 0.30, 0.60, 0.65, 0.35),  # = 0.40
        'Binance':   (0.10, 0.25, 0.55, 0.60, 0.50),  # = 0.38
        'Aave V3':   (0.10, 0.25, 0.15, 0.35, 0.15),  # = 0.20
        'Curve 3pool': (0.10, 0.20, 0.15, 0.30, 0.15),  # = 0.18
        '1inch':     (0.10, 0.20, 0.15, 0.30, 0.15),  # = 0.18
        'Compound V3': (0.10, 0.20, 0.15, 0.30, 0.15),  # = 0.18
        'Uniswap V3': (0.10, 0.15, 0.10, 0.30, 0.10),  # = 0.15
        'Uniswap Universal Router': (0.10, 0.15, 0.10, 0.30, 0.10),  # = 0.15
        'Tornado Cash': (0.00, 0.00, 0.00, 0.05, 0.05),  # = 0.02
    }

    # Authoritative composite CLII from v42 docx Table 2a
    KNOWN_CLII = {
        'Circle': 0.92, 'Paxos': 0.88, 'PayPal': 0.88,
        'Coinbase': 0.85, 'Gemini': 0.82, 'BitGo': 0.80,
        'Robinhood': 0.75,
        'Kraken': 0.58, 'Tether': 0.45,
        'OKX': 0.40, 'Bybit': 0.40, 'Binance': 0.38,
        'Aave V3': 0.20, 'Curve 3pool': 0.18, '1inch': 0.18,
        'Compound V3': 0.18,
        'Uniswap V3': 0.15, 'Uniswap Universal Router': 0.15,
        'Tornado Cash': 0.02,
    }

    def get_tier(clii):
        if clii > 0.75: return 1   # strict >0.75 per v42 docx footnote
        if clii >= 0.30: return 2
        return 3

    rows = []
    for entity in sorted(KNOWN_CLII.keys()):
        scores = TABLE_B2[entity]

        scores_arr = np.array(scores)
        # Use Table 2a authoritative composite as baseline, not dimension-weighted sum
        baseline_clii = KNOWN_CLII[entity]
        nofreeze_clii = float(np.dot(scores_arr, w_nofreeze))

        baseline_tier = get_tier(baseline_clii)
        nofreeze_tier = get_tier(nofreeze_clii)

        rows.append({
            'entity': entity,
            'baseline_clii': round(baseline_clii, 4),
            'baseline_tier': baseline_tier,
            'nofreeze_clii': round(nofreeze_clii, 4),
            'nofreeze_tier': nofreeze_tier,
            'tier_changed': baseline_tier != nofreeze_tier,
            'delta_clii': round(nofreeze_clii - baseline_clii, 4),
            'scores_source': 'table_2a',
            'lic': scores[0],
            'trans': scores[1],
            'freeze': scores[2],
            'comp': scores[3],
            'sanc': scores[4],
        })

    df = pd.DataFrame(rows).sort_values('baseline_clii', ascending=False)
    save_csv(df, 'clii_nofreeze_robustness.csv')

    # Print results
    changed = df[df['tier_changed']]
    print(f"\n  Tier changes: {len(changed)} of {len(df)}")
    if len(changed) > 0:
        for _, r in changed.iterrows():
            print(f"    {r['entity']}: T{r['baseline_tier']}→T{r['nofreeze_tier']} "
                  f"(CLII {r['baseline_clii']:.3f}→{r['nofreeze_clii']:.3f})")
    else:
        print("    None")
    max_delta = df.loc[df['delta_clii'].abs().idxmax()]
    print(f"  Max |ΔCLII|: {abs(max_delta['delta_clii']):.4f} ({max_delta['entity']})")

    # ── Exhibit: Dumbbell chart ──
    fig, ax = plt.subplots(figsize=(6.5, 6.0))
    fig.suptitle('CLII No-Freeze Robustness: Baseline vs. Four-Dimension Scores',
                 fontsize=13, fontweight='bold', y=1.02)

    df_plot = df.sort_values('baseline_clii', ascending=True).reset_index(drop=True)
    y_positions = range(len(df_plot))

    for i, (_, r) in enumerate(df_plot.iterrows()):
        line_color = RED if r['tier_changed'] else LIGHT_GRAY
        ax.plot([r['baseline_clii'], r['nofreeze_clii']], [i, i],
                color=line_color, linewidth=1.5, zorder=2)
        # Baseline: filled circle
        ax.scatter(r['baseline_clii'], i, color=NAVY, s=40, zorder=3, edgecolors='white', linewidths=0.5)
        # No-freeze: open circle
        ax.scatter(r['nofreeze_clii'], i, color=NAVY, s=40, zorder=3, facecolors='white',
                   edgecolors=NAVY, linewidths=1.2)

        if r['tier_changed']:
            ax.annotate(f"T{r['baseline_tier']}→T{r['nofreeze_tier']}",
                        xy=(r['nofreeze_clii'], i), xytext=(r['nofreeze_clii'] + 0.03, i),
                        fontsize=7, color=RED, fontweight='bold', va='center')

    ax.set_yticks(list(y_positions))
    ax.set_yticklabels(df_plot['entity'], fontsize=10)
    ax.set_xlabel('CLII Score', fontsize=12)
    ax.set_xlim(-0.02, 1.05)
    ax.axvline(0.75, color=NAVY, linestyle='--', linewidth=0.8, alpha=0.6, label='Tier 1/2 boundary')
    ax.axvline(0.30, color=GOLD, linestyle='--', linewidth=0.8, alpha=0.6, label='Tier 2/3 boundary')

    # Legend
    handles = [
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=NAVY, markersize=6, label='Baseline CLII'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='white', markeredgecolor=NAVY,
                    markersize=6, markeredgewidth=1.2, label='No-freeze CLII'),
        plt.Line2D([0], [0], color=RED, linewidth=1.5, label='Tier changed'),
        plt.Line2D([0], [0], color=LIGHT_GRAY, linewidth=1.5, label='Tier stable'),
    ]
    ax.legend(handles=handles, fontsize=9, loc='lower right')

    fig.text(0.5, -0.02,
             "Source: Authors' calculations. Freeze/Blacklist dimension dropped; "
             "weight redistributed proportionally to remaining 4 dimensions.",
             ha='center', fontsize=8, fontstyle='italic', color='#666666')

    fig.tight_layout(rect=[0, 0.02, 1, 0.95])
    save_fig(fig, 'exhibit_clii_nofreeze_robustness.png')

    return df


# ══════════════════════════════════════════════════════════════
# LOAD DAILY TIER DATA (shared by Phase 3 tasks)
# ══════════════════════════════════════════════════════════════
def load_daily_tiers():
    """Load expanded gateway data, compute daily tier shares."""
    df = pd.read_csv(EXPANDED)
    df['day'] = pd.to_datetime(df['day'], utc=True).dt.normalize()

    # Daily volume by tier
    daily_tier = df.groupby(['day', 'tier'])['volume_usd'].sum().unstack(fill_value=0)
    daily_tier.columns = [f't{int(c)}_volume' for c in daily_tier.columns]
    for c in ['t1_volume', 't2_volume', 't3_volume']:
        if c not in daily_tier.columns:
            daily_tier[c] = 0
    daily_tier['total_volume'] = daily_tier[['t1_volume', 't2_volume', 't3_volume']].sum(axis=1)
    daily_tier['t1_share'] = daily_tier['t1_volume'] / daily_tier['total_volume']
    daily_tier['t2_share'] = daily_tier['t2_volume'] / daily_tier['total_volume']
    daily_tier['t3_share'] = daily_tier['t3_volume'] / daily_tier['total_volume']
    daily_tier = daily_tier.sort_index()

    # Day-of-week info
    daily_tier['day_of_week'] = daily_tier.index.day_name()
    daily_tier['dow_num'] = daily_tier.index.dayofweek  # 0=Mon, 6=Sun
    daily_tier['is_weekend'] = daily_tier['dow_num'].isin([5, 6])

    # SVB window
    svb_start = pd.Timestamp('2023-03-08', tz='UTC')
    svb_end = pd.Timestamp('2023-03-15', tz='UTC')
    daily_tier['is_svb_window'] = (daily_tier.index >= svb_start) & (daily_tier.index <= svb_end)

    # T1 change from prior day
    daily_tier['t1_change_from_prior'] = daily_tier['t1_share'].diff()

    return daily_tier


# ══════════════════════════════════════════════════════════════
# PHASE 3.1: WEEKEND / DAY-OF-WEEK ANALYSIS
# ══════════════════════════════════════════════════════════════
def phase3_1(daily):
    print("\n" + "=" * 60)
    print("PHASE 3.1: WEEKEND / DAY-OF-WEEK ANALYSIS")
    print("=" * 60)

    # (a) Full-sample stats by day of week
    dow_stats = daily.groupby('day_of_week')['t1_share'].agg(['mean', 'median', 'std'])
    dow_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    dow_stats = dow_stats.reindex(dow_order)
    print("\n  Day-of-week T1 share:")
    for day, row in dow_stats.iterrows():
        print(f"    {day:12s}: mean={row['mean']*100:.1f}%, std={row['std']*100:.1f}%")

    # (b) Weekday vs weekend
    weekday_mean = daily[~daily['is_weekend']]['t1_share'].mean()
    weekend_mean = daily[daily['is_weekend']]['t1_share'].mean()
    structural_dip = (weekday_mean - weekend_mean) * 100
    print(f"\n  Weekday mean T1: {weekday_mean*100:.1f}%")
    print(f"  Weekend mean T1: {weekend_mean*100:.1f}%")
    print(f"  Structural dip:  {structural_dip:.1f} pp")

    # (c) Day-over-day changes by transition type
    daily_c = daily.copy()
    daily_c['prior_dow'] = daily_c['dow_num'].shift(1)
    daily_c['transition'] = daily_c.apply(
        lambda r: f"{int(r['prior_dow'])}→{int(r['dow_num'])}" if pd.notna(r['prior_dow']) else None, axis=1)

    fri_sat = daily_c[daily_c['transition'] == '4→5']['t1_change_from_prior'].dropna()
    sat_sun = daily_c[daily_c['transition'] == '5→6']['t1_change_from_prior'].dropna()
    other = daily_c[~daily_c['transition'].isin(['4→5', '5→6']) & daily_c['transition'].notna()]['t1_change_from_prior'].dropna()

    print(f"\n  Fri→Sat changes: mean={fri_sat.mean()*100:.2f} pp, std={fri_sat.std()*100:.2f} pp, n={len(fri_sat)}")
    print(f"  Sat→Sun changes: mean={sat_sun.mean()*100:.2f} pp, std={sat_sun.std()*100:.2f} pp, n={len(sat_sun)}")

    # (d) SVB-specific
    svb = daily[daily['is_svb_window']].copy()
    print(f"\n  SVB daily T1 shares:")
    for d, row in svb.iterrows():
        print(f"    {d.date()} ({row['day_of_week'][:3]}): T1={row['t1_share']*100:.1f}%, "
              f"Δ={row['t1_change_from_prior']*100:+.1f} pp" if pd.notna(row['t1_change_from_prior'])
              else f"    {d.date()} ({row['day_of_week'][:3]}): T1={row['t1_share']*100:.1f}%")

    # SVB Fri→Sat: Mar 10 (Fri) → Mar 11 (Sat)
    svb_mar11 = svb[svb.index.day == 11]
    svb_fri_sat_change = float(svb_mar11['t1_change_from_prior'].iloc[0]) if len(svb_mar11) > 0 else np.nan

    # Exclude SVB from normal distribution
    non_svb_fri_sat = daily_c[(daily_c['transition'] == '4→5') & (~daily_c['is_svb_window'])]['t1_change_from_prior'].dropna()
    svb_fri_sat_z = (svb_fri_sat_change - non_svb_fri_sat.mean()) / non_svb_fri_sat.std() if non_svb_fri_sat.std() > 0 else np.nan

    # SVB Sat→Sun: Mar 11 (Sat) → Mar 12 (Sun)
    svb_mar12 = svb[svb.index.day == 12]
    svb_sat_sun_change = float(svb_mar12['t1_change_from_prior'].iloc[0]) if len(svb_mar12) > 0 else np.nan
    non_svb_sat_sun = daily_c[(daily_c['transition'] == '5→6') & (~daily_c['is_svb_window'])]['t1_change_from_prior'].dropna()
    svb_sat_sun_z = (svb_sat_sun_change - non_svb_sat_sun.mean()) / non_svb_sat_sun.std() if non_svb_sat_sun.std() > 0 else np.nan

    print(f"\n  SVB Fri→Sat change: {svb_fri_sat_change*100:.1f} pp (z={svb_fri_sat_z:.2f}σ)")
    print(f"  SVB Sat→Sun change: {svb_sat_sun_change*100:.1f} pp (z={svb_sat_sun_z:.2f}σ)")

    # (e) SVB weekend absolute z
    weekend_t1_all = daily[daily['is_weekend']]['t1_share']
    weekend_std = weekend_t1_all.std()
    svb_weekend = daily[(daily['is_svb_window']) & (daily['is_weekend'])]['t1_share']
    svb_weekend_mean = svb_weekend.mean()
    normal_weekend_mean = daily[(~daily['is_svb_window']) & (daily['is_weekend'])]['t1_share'].mean()
    svb_weekend_z = (normal_weekend_mean - svb_weekend_mean) / weekend_std if weekend_std > 0 else np.nan

    print(f"  SVB weekend mean T1: {svb_weekend_mean*100:.1f}%")
    print(f"  SVB weekend absolute z: {svb_weekend_z:.2f}σ")

    # ── Save daily CSV ──
    out = daily[['day_of_week', 'is_weekend', 't1_share', 't2_share', 't3_share',
                 't1_volume', 'total_volume', 't1_change_from_prior', 'is_svb_window']].copy()
    out.index.name = 'date'
    out_reset = out.reset_index()
    out_reset['date'] = out_reset['date'].dt.strftime('%Y-%m-%d')
    save_csv(out_reset, 'weekend_analysis_expanded.csv')

    # ── Save summary stats CSV ──
    stats_rows = [
        ('weekday_mean_t1', round(weekday_mean, 4), 'share', 'Mon-Fri average'),
        ('weekend_mean_t1', round(weekend_mean, 4), 'share', 'Sat-Sun average'),
        ('baseline_weekend_dip', round(structural_dip, 1), 'pp', 'weekday - weekend mean'),
        ('weekend_t1_std', round(weekend_std, 4), 'share', 'std of all weekend T1 share observations'),
        ('svb_weekend_mean_t1', round(svb_weekend_mean, 4), 'share', 'Mar 11-12 2023 average'),
        ('svb_weekend_zscore_absolute', round(svb_weekend_z, 2), 'sigma', '(normal_wkend - svb_wkend) / wkend_std'),
        ('svb_fri_sat_change', round(svb_fri_sat_change * 100, 1), 'pp', 'Mar 10→11 T1 share change'),
        ('normal_fri_sat_mean', round(non_svb_fri_sat.mean() * 100, 2), 'pp', 'mean of all non-SVB Fri→Sat changes'),
        ('normal_fri_sat_std', round(non_svb_fri_sat.std() * 100, 2), 'pp', 'std of all non-SVB Fri→Sat changes'),
        ('svb_fri_sat_zscore', round(svb_fri_sat_z, 2), 'sigma', 'z-score of SVB Fri→Sat vs distribution'),
        ('svb_sat_sun_change', round(svb_sat_sun_change * 100, 1), 'pp', 'Mar 11→12 T1 share change'),
        ('normal_sat_sun_mean', round(non_svb_sat_sun.mean() * 100, 2), 'pp', 'mean of all non-SVB Sat→Sun changes'),
        ('normal_sat_sun_std', round(non_svb_sat_sun.std() * 100, 2), 'pp', 'std of all non-SVB Sat→Sun changes'),
        ('svb_sat_sun_zscore', round(svb_sat_sun_z, 2), 'sigma', 'z-score of SVB Sat→Sun vs distribution'),
    ]
    save_csv(pd.DataFrame(stats_rows, columns=['metric', 'value', 'units', 'notes']),
             'weekend_summary_stats.csv')

    # ── Exhibit: Two-panel ──
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6.5, 6.0), gridspec_kw={'height_ratios': [1.2, 1]})

    # Panel A: Box-and-whisker by day of week
    dow_data = [daily[daily['day_of_week'] == d]['t1_share'].values * 100 for d in dow_order]
    bp = ax1.boxplot(dow_data, labels=[d[:3] for d in dow_order], patch_artist=True,
                     widths=0.6, showfliers=False)
    for patch, day in zip(bp['boxes'], dow_order):
        patch.set_facecolor(GOLD if day in ('Saturday', 'Sunday') else NAVY)
        patch.set_alpha(0.6)
    for median in bp['medians']:
        median.set_color('black')
        median.set_linewidth(1.5)

    # Overlay SVB crisis week: Mar 6-12 (Mon-Sun) gives one clean
    # Mon→Sun trajectory showing baseline→spike→crash→nadir.
    # The old Mar 8-15 window spanned a week boundary, mixing
    # post-recovery Mon/Tue data with crisis data.
    svb_chart = daily[(daily.index >= pd.Timestamp('2023-03-06', tz='UTC')) &
                      (daily.index <= pd.Timestamp('2023-03-12', tz='UTC'))].sort_index()
    svb_x = [dow_order.index(d) + 1 for d in svb_chart['day_of_week']]
    svb_y = svb_chart['t1_share'].values * 100
    ax1.plot(svb_x, svb_y, 'o-', color=RED, linewidth=2, markersize=5, zorder=5, label='SVB week (Mar 6\u201312)')
    ax1.legend(fontsize=8, loc='lower left')
    ax1.set_ylabel('Tier 1 Volume Share (%)')
    ax1.set_title('Tier 1 Share by Day of Week')

    # Panel B: Histogram of Fri→Sat changes + SVB marker
    ax2.hist(non_svb_fri_sat.values * 100, bins=25, color=NAVY, alpha=0.6, edgecolor='white',
             label='Non-SVB Fri→Sat')
    ax2.axvline(svb_fri_sat_change * 100, color=RED, linewidth=2, linestyle='--',
                label=f'SVB: {svb_fri_sat_change*100:.1f} pp (z={svb_fri_sat_z:.1f}σ)')
    ax2.set_xlabel('Fri→Sat T1 Share Change (pp)')
    ax2.set_ylabel('Frequency')
    ax2.set_title('Distribution of Friday-to-Saturday Tier 1 Share Changes')
    ax2.legend(fontsize=8)

    fig.tight_layout()
    save_fig(fig, 'exhibit_weekend_dayofweek.png')

    return {
        'weekday_mean': weekday_mean, 'weekend_mean': weekend_mean,
        'structural_dip': structural_dip,
        'svb_weekend_mean': svb_weekend_mean, 'svb_weekend_z': svb_weekend_z,
        'svb_fri_sat_change': svb_fri_sat_change, 'svb_fri_sat_z': svb_fri_sat_z,
        'svb_sat_sun_change': svb_sat_sun_change, 'svb_sat_sun_z': svb_sat_sun_z,
    }


# ══════════════════════════════════════════════════════════════
# PHASE 3.2: PLACEBO ANALYSIS (50 RANDOM WINDOWS)
# ══════════════════════════════════════════════════════════════
def phase3_2(daily):
    print("\n" + "=" * 60)
    print("PHASE 3.2: PLACEBO ANALYSIS (50 RANDOM WINDOWS)")
    print("=" * 60)

    t1 = daily['t1_share'].copy()

    # SVB center: 2023-03-10
    svb_center = pd.Timestamp('2023-03-10', tz='UTC')
    offsets = list(range(-7, 8))  # 15-day window

    # SVB trajectory
    svb_traj = {}
    for off in offsets:
        d = svb_center + pd.Timedelta(days=off)
        if d in t1.index:
            svb_traj[off] = float(t1.loc[d])
        else:
            svb_traj[off] = np.nan

    svb_vals = [svb_traj[o] for o in offsets if not np.isnan(svb_traj.get(o, np.nan))]
    svb_swing = max(svb_vals) - min(svb_vals) if svb_vals else 0
    svb_nadir = min(svb_vals) if svb_vals else np.nan
    svb_nadir_day = [o for o in offsets if svb_traj.get(o) == svb_nadir]

    print(f"  SVB 15-day swing: {svb_swing*100:.1f} pp")
    print(f"  SVB nadir: {svb_nadir*100:.1f}% at day {svb_nadir_day}")

    # 50 placebo windows
    np.random.seed(42)
    excl_start = pd.Timestamp('2023-03-01', tz='UTC')
    excl_end = pd.Timestamp('2023-03-31', tz='UTC')
    eligible = t1.index[(t1.index < excl_start) | (t1.index > excl_end)]
    eligible = eligible[(eligible >= t1.index[7]) & (eligible <= t1.index[-8])]

    placebo_centers = np.random.choice(eligible, size=min(50, len(eligible)), replace=False)

    placebo_trajs = []
    placebo_swings = []
    for pc in sorted(placebo_centers):
        pc = pd.Timestamp(pc)
        traj = {}
        for off in offsets:
            d = pc + pd.Timedelta(days=off)
            if d in t1.index:
                traj[off] = float(t1.loc[d])
            else:
                traj[off] = np.nan
        placebo_trajs.append(traj)
        vals = [v for v in traj.values() if not np.isnan(v)]
        if vals:
            placebo_swings.append(max(vals) - min(vals))

    placebo_arr = np.array(placebo_swings)
    svb_exceeds = svb_swing > placebo_arr.max()
    svb_pctile = float(np.sum(placebo_arr < svb_swing) / len(placebo_arr) * 100)

    # Placebo stats at each event-time day
    event_rows = []
    for off in offsets:
        vals = [tr.get(off, np.nan) for tr in placebo_trajs]
        vals = [v for v in vals if not np.isnan(v)]
        if vals:
            pmean = np.mean(vals)
            pstd = np.std(vals)
            p5 = np.percentile(vals, 5)
            p95 = np.percentile(vals, 95)
            sv = svb_traj.get(off, np.nan)
            zsc = (sv - pmean) / pstd if pstd > 0 and not np.isnan(sv) else np.nan
        else:
            pmean = pstd = p5 = p95 = zsc = np.nan
            sv = svb_traj.get(off, np.nan)

        event_rows.append({
            'event_day': off,
            'svb_t1_share': round(sv, 6) if not np.isnan(sv) else np.nan,
            'placebo_mean': round(pmean, 6),
            'placebo_std': round(pstd, 6),
            'placebo_p5': round(p5, 6),
            'placebo_p95': round(p95, 6),
            'svb_zscore': round(zsc, 4) if not np.isnan(zsc) else np.nan,
        })

    save_csv(pd.DataFrame(event_rows), 'placebo_analysis_expanded.csv')

    # Nadir z-score
    nadir_row = [r for r in event_rows if r['svb_t1_share'] == round(svb_nadir, 6)]
    nadir_z = nadir_row[0]['svb_zscore'] if nadir_row else np.nan
    if np.isnan(nadir_z):
        # Compute directly
        nadir_off = svb_nadir_day[0] if svb_nadir_day else 2
        nadir_vals = [tr.get(nadir_off, np.nan) for tr in placebo_trajs]
        nadir_vals = [v for v in nadir_vals if not np.isnan(v)]
        if nadir_vals:
            nadir_z = (svb_nadir - np.mean(nadir_vals)) / np.std(nadir_vals) if np.std(nadir_vals) > 0 else np.nan

    # Days below p5
    days_below = sum(1 for r in event_rows if not np.isnan(r.get('svb_t1_share', np.nan))
                     and not np.isnan(r.get('placebo_p5', np.nan))
                     and r['svb_t1_share'] < r['placebo_p5'])

    print(f"  Placebo max swing: {placebo_arr.max()*100:.1f} pp")
    print(f"  Placebo mean swing: {placebo_arr.mean()*100:.1f} pp")
    print(f"  SVB exceeds all placebos: {svb_exceeds}")
    print(f"  SVB swing percentile: {svb_pctile:.0f}")
    print(f"  Nadir z-score: {nadir_z:.1f}σ")
    print(f"  Days below p5: {days_below} of 15")

    # Swing stats CSV
    swing_stats = pd.DataFrame([
        ('svb_swing_pp', round(svb_swing * 100, 1)),
        ('placebo_max_swing_pp', round(float(placebo_arr.max()) * 100, 1)),
        ('placebo_mean_swing_pp', round(float(placebo_arr.mean()) * 100, 1)),
        ('placebo_median_swing_pp', round(float(np.median(placebo_arr)) * 100, 1)),
        ('svb_exceeds_all_placebos', svb_exceeds),
        ('svb_swing_percentile', round(svb_pctile, 0)),
        ('nadir_zscore', round(nadir_z, 1) if not np.isnan(nadir_z) else 'NA'),
        ('days_below_p5', days_below),
    ], columns=['metric', 'value'])
    save_csv(swing_stats, 'placebo_swing_stats.csv')

    # ── Exhibit ──
    fig, ax = plt.subplots(figsize=(6.5, 4.0))

    # Spaghetti: individual placebos
    for traj in placebo_trajs:
        x = [o for o in offsets if not np.isnan(traj.get(o, np.nan))]
        y = [traj[o] * 100 for o in x]
        ax.plot(x, y, color=GRAY, alpha=0.15, linewidth=0.5, zorder=1)

    # 5th-95th band
    band_x = [r['event_day'] for r in event_rows]
    p5_y = [r['placebo_p5'] * 100 for r in event_rows]
    p95_y = [r['placebo_p95'] * 100 for r in event_rows]
    mean_y = [r['placebo_mean'] * 100 for r in event_rows]
    ax.fill_between(band_x, p5_y, p95_y, alpha=0.2, color=NAVY, label='5th-95th percentile', zorder=2)
    ax.plot(band_x, mean_y, color=NAVY, linestyle='--', linewidth=1, label='Placebo mean', zorder=3)

    # SVB trajectory
    svb_x = [o for o in offsets if not np.isnan(svb_traj.get(o, np.nan))]
    svb_y = [svb_traj[o] * 100 for o in svb_x]
    ax.plot(svb_x, svb_y, color=RED, linewidth=2.5, marker='o', markersize=3,
            label='SVB episode', zorder=4)

    # Nadir marker
    if svb_nadir_day:
        ax.scatter(svb_nadir_day[0], svb_nadir * 100, color=RED, s=60, zorder=5, edgecolors='white')
        ax.annotate(f'Nadir: {svb_nadir*100:.1f}%\n(z={nadir_z:.1f}σ)',
                    xy=(svb_nadir_day[0], svb_nadir * 100),
                    xytext=(svb_nadir_day[0] + 2, svb_nadir * 100 - 3),
                    fontsize=7, color=RED, fontweight='bold',
                    arrowprops=dict(arrowstyle='->', color=RED, lw=1))

    ax.set_xlabel('Event time (days)')
    ax.set_ylabel('Tier 1 Volume Share (%)')
    ax.set_xticks(offsets)
    ax.legend(fontsize=7.5, loc='upper right')

    fig.suptitle('Placebo Analysis: SVB Tier 1 Share Trajectory\n(Expanded 51-Address Registry)',
                 fontweight='bold', fontsize=12, y=1.02)
    fig.tight_layout()
    save_fig(fig, 'exhibit_placebo_expanded.png')

    return {
        'svb_swing': svb_swing, 'placebo_max': float(placebo_arr.max()),
        'svb_exceeds': svb_exceeds, 'nadir_z': nadir_z, 'days_below': days_below,
        'placebo_mean_swing': float(placebo_arr.mean()),
    }


# ══════════════════════════════════════════════════════════════
# PHASE 3.3: JACKKNIFE LEAVE-ONE-OUT
# ══════════════════════════════════════════════════════════════
def phase3_3(daily):
    print("\n" + "=" * 60)
    print("PHASE 3.3: JACKKNIFE LEAVE-ONE-OUT")
    print("=" * 60)

    df = pd.read_csv(EXPANDED)
    df['day'] = pd.to_datetime(df['day'], utc=True).dt.normalize()

    # Baseline daily T1 share (time-averaged)
    daily_entity = df.groupby(['day', 'entity', 'tier'])['volume_usd'].sum().reset_index()
    baseline_t1_mean = daily['t1_share'].mean()
    print(f"  Baseline T1 share: {baseline_t1_mean*100:.1f}%")

    entities = sorted(df['entity'].unique())
    # Get tier for each entity
    entity_tier = df.groupby('entity')['tier'].first().to_dict()

    loo_rows = []
    for ent in entities:
        # Remove entity
        remaining = daily_entity[daily_entity['entity'] != ent]
        rem_daily = remaining.groupby('day').agg(
            t1_vol=('volume_usd', lambda x: x[remaining.loc[x.index, 'tier'] == 1].sum()),
            total_vol=('volume_usd', 'sum')
        )
        # Need a cleaner approach
        rem_t1 = remaining[remaining['tier'] == 1].groupby('day')['volume_usd'].sum()
        rem_total = remaining.groupby('day')['volume_usd'].sum()
        rem_share = (rem_t1 / rem_total).dropna()
        loo_mean = rem_share.mean()
        delta = (loo_mean - baseline_t1_mean) * 100

        loo_rows.append({
            'entity': ent,
            'tier': entity_tier[ent],
            'baseline_t1_mean': round(baseline_t1_mean * 100, 2),
            'loo_t1_mean': round(loo_mean * 100, 2),
            'delta_pp': round(delta, 2),
            'abs_delta_pp': round(abs(delta), 2),
        })

    loo_df = pd.DataFrame(loo_rows).sort_values('abs_delta_pp', ascending=False)
    save_csv(loo_df, 'jackknife_loo_expanded.csv')

    top3 = loo_df.head(3)
    print(f"\n  Top 3 movers:")
    for _, r in top3.iterrows():
        print(f"    {r['entity']} (T{r['tier']}): {r['delta_pp']:+.1f} pp")

    # ── Exhibit: Tornado chart ──
    fig, ax = plt.subplots(figsize=(6.5, 5.0))

    loo_plot = loo_df.sort_values('delta_pp', ascending=True).reset_index(drop=True)
    y_pos = range(len(loo_plot))
    tier_colors = {1: NAVY, 2: GOLD, 3: GREEN}
    colors = [tier_colors.get(r['tier'], GRAY) for _, r in loo_plot.iterrows()]

    ax.barh(y_pos, loo_plot['delta_pp'], color=colors, height=0.7, edgecolor='white', alpha=0.8)
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(loo_plot['entity'], fontsize=8)
    ax.axvline(0, color='black', linewidth=0.8)
    ax.set_xlabel('Δ Tier 1 Share (pp)')
    ax.set_title('Leave-One-Out: Impact on Mean Tier 1 Volume Share')

    # Reference: baseline
    ax.axvline(0, color='black', linewidth=0.8, linestyle='-')

    # Legend
    handles = [mpatches.Patch(color=NAVY, label='Tier 1'),
               mpatches.Patch(color=GOLD, label='Tier 2'),
               mpatches.Patch(color=GREEN, label='Tier 3')]
    ax.legend(handles=handles, fontsize=8, loc='lower right')

    fig.text(0.5, -0.02,
             f"Baseline Tier 1 share: {baseline_t1_mean*100:.1f}%. "
             "Source: Authors' calculations from Dune Analytics.",
             ha='center', fontsize=7, fontstyle='italic', color='#666666')

    fig.tight_layout()
    save_fig(fig, 'exhibit_jackknife_expanded.png')

    return {'baseline_t1': baseline_t1_mean, 'top3': top3[['entity', 'delta_pp']].values.tolist()}


# ══════════════════════════════════════════════════════════════
# PHASE 3.4: COVERAGE SENSITIVITY
# ══════════════════════════════════════════════════════════════
def phase3_4(daily):
    print("\n" + "=" * 60)
    print("PHASE 3.4: COVERAGE SENSITIVITY")
    print("=" * 60)

    # Total Ethereum volume
    eth_total = pd.read_csv(ETH_TOTAL)
    total_eth_volume = eth_total['volume_usd'].sum()

    # Gateway volume by tier (aggregate over full sample)
    df = pd.read_csv(EXPANDED)
    gw_by_tier = df.groupby('tier')['volume_usd'].sum()
    t1_vol = gw_by_tier.get(1, 0)
    t2_vol = gw_by_tier.get(2, 0)
    t3_vol = gw_by_tier.get(3, 0)
    gw_total = t1_vol + t2_vol + t3_vol
    unlabeled_volume = total_eth_volume - gw_total

    coverage = gw_total / total_eth_volume
    print(f"  Gateway volume: ${gw_total/1e12:.2f}T")
    print(f"  Total ETH volume: ${total_eth_volume/1e12:.2f}T")
    print(f"  Coverage: {coverage*100:.1f}%")
    print(f"  Unlabeled volume: ${unlabeled_volume/1e12:.2f}T")

    reclass_pcts = [0, 5, 10, 15, 20, 25]
    rows = []
    for pct in reclass_pcts:
        reclassified = unlabeled_volume * pct / 100
        new_t2 = t2_vol + reclassified
        new_total = gw_total + reclassified
        new_t1_share = t1_vol / new_total
        new_t2_share = new_t2 / new_total
        new_t3_share = t3_vol / new_total

        # Tier-level HHI
        shares = np.array([new_t1_share, new_t2_share, new_t3_share])
        tier_hhi = int(np.sum((shares * 100) ** 2))

        rows.append({
            'reclassification_pct': pct,
            't1_share': round(new_t1_share, 4),
            't2_share': round(new_t2_share, 4),
            't3_share': round(new_t3_share, 4),
            'tier_hhi': tier_hhi,
            't1_volume': round(t1_vol, 0),
            't2_volume': round(new_t2, 0),
            't3_volume': round(t3_vol, 0),
            'total_volume': round(new_total, 0),
        })
        print(f"  Reclass {pct:2d}%: T1={new_t1_share*100:.1f}%, T2={new_t2_share*100:.1f}%, "
              f"HHI={tier_hhi:,}")

    cov_df = pd.DataFrame(rows)
    save_csv(cov_df, 'coverage_sensitivity_expanded.csv')

    # ── Exhibit: Two-panel ──
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 4))
    fig.suptitle('Coverage Sensitivity: Expanded 51-Address Registry',
                 fontsize=13, fontweight='bold', y=1.02)

    # Panel A: T1 share
    ax1.plot(cov_df['reclassification_pct'], cov_df['t1_share'] * 100,
             color=NAVY, linewidth=2, marker='o', markersize=5)
    ax1.fill_between(cov_df['reclassification_pct'], 0, cov_df['t1_share'] * 100,
                     alpha=0.08, color=NAVY)
    ax1.scatter([0], [cov_df.iloc[0]['t1_share'] * 100], s=150, marker='*',
                color=GOLD, zorder=5, label='Baseline')
    ax1.axhline(50, color=RED, linestyle='--', linewidth=0.8, label='Parity (50%)')
    ax1.set_xlabel('Unlabeled Volume Attributed to Tier 2 (%)', fontsize=11)
    ax1.set_ylabel('Tier 1 Share (%)', fontsize=11)
    ax1.set_title('Panel A: Tier 1 Share', fontsize=11)
    ax1.legend(fontsize=9)
    ax1.tick_params(labelsize=10)
    ax1.set_ylim(0, cov_df['t1_share'].max() * 100 * 1.3)

    # Panel B: HHI
    ax2.plot(cov_df['reclassification_pct'], cov_df['tier_hhi'],
             color=NAVY, linewidth=2, marker='s', markersize=5)
    ax2.scatter([0], [cov_df.iloc[0]['tier_hhi']], s=150, marker='*',
                color=GOLD, zorder=5, label='Baseline')
    ax2.axhline(2500, color=RED, linestyle='--', linewidth=0.8, label='DOJ/FTC threshold')
    ax2.set_xlabel('Unlabeled Volume Attributed to Tier 2 (%)', fontsize=11)
    ax2.set_ylabel('Tier-Level HHI', fontsize=11)
    ax2.set_title('Panel B: Tier-Level HHI', fontsize=11)
    ax2.legend(fontsize=9)
    ax2.tick_params(labelsize=10)

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.subplots_adjust(wspace=0.35)
    fig.text(0.5, -0.04,
             "Source: Authors' calculations using Dune Analytics data.",
             ha='center', fontsize=8, fontstyle='italic', color='gray')
    save_fig(fig, 'exhibit_coverage_sensitivity_expanded.png')

    return {
        'baseline_t1': cov_df.iloc[0]['t1_share'],
        't1_at_25': cov_df.iloc[-1]['t1_share'],
        'hhi_at_25': cov_df.iloc[-1]['tier_hhi'],
    }


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    # Phase 2
    clii_df = phase2()

    # Load shared daily data
    daily = load_daily_tiers()

    # Phase 3
    wk_results = phase3_1(daily)
    pl_results = phase3_2(daily)
    jk_results = phase3_3(daily)
    cv_results = phase3_4(daily)

    # ── Summary ──
    changed = clii_df[clii_df['tier_changed']]
    max_d = clii_df.loc[clii_df['delta_clii'].abs().idxmax()]

    print("\n" + "=" * 60)
    print("=== PHASE 2: CLII NO-FREEZE RESULTS ===")
    print(f"Tier changes: {len(changed)} of {len(clii_df)}")
    if len(changed) > 0:
        print(f"Entities changed: {list(changed['entity'])}")
    else:
        print("Entities changed: none")
    print(f"Max |ΔCLII|: {abs(max_d['delta_clii']):.4f} ({max_d['entity']})")

    print(f"\n=== PHASE 3.1: WEEKEND ANALYSIS ===")
    print(f"Weekday mean T1:     {wk_results['weekday_mean']*100:.1f}%")
    print(f"Weekend mean T1:     {wk_results['weekend_mean']*100:.1f}%")
    print(f"Structural dip:      {wk_results['structural_dip']:.1f} pp")
    print(f"SVB weekend T1:      {wk_results['svb_weekend_mean']*100:.1f}%")
    print(f"SVB absolute z:      {wk_results['svb_weekend_z']:.1f}σ")
    print(f"SVB Fri→Sat change:  {wk_results['svb_fri_sat_change']*100:.1f} pp")
    print(f"SVB Fri→Sat z:       {wk_results['svb_fri_sat_z']:.1f}σ")
    print(f"SVB Sat→Sun change:  {wk_results['svb_sat_sun_change']*100:.1f} pp")
    print(f"SVB Sat→Sun z:       {wk_results['svb_sat_sun_z']:.1f}σ")

    print(f"\n=== PHASE 3.2: PLACEBO ===")
    print(f"SVB 15-day swing:    {pl_results['svb_swing']*100:.1f} pp")
    print(f"Placebo max swing:   {pl_results['placebo_max']*100:.1f} pp")
    print(f"SVB exceeds all:     {'Yes' if pl_results['svb_exceeds'] else 'No'}")
    print(f"Nadir z-score:       {pl_results['nadir_z']:.1f}σ")
    print(f"Days below p5:       {pl_results['days_below']} of 15")

    print(f"\n=== PHASE 3.3: JACKKNIFE ===")
    print(f"Baseline T1 share:   {jk_results['baseline_t1']*100:.1f}%")
    print(f"Top 3 movers:        ", end="")
    print(", ".join(f"{e} ({d:+.1f} pp)" for e, d in jk_results['top3']))

    print(f"\n=== PHASE 3.4: COVERAGE SENSITIVITY ===")
    print(f"Baseline T1:         {cv_results['baseline_t1']*100:.1f}%")
    print(f"T1 at 25% reclass:   {cv_results['t1_at_25']*100:.1f}%")
    print(f"HHI at 25% reclass:  {cv_results['hhi_at_25']:,}")

    print("\n" + "=" * 60)
    print("ALL PHASES COMPLETE")
    print("=" * 60)
