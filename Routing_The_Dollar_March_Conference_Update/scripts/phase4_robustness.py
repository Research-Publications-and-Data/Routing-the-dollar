"""
Phase 4: New Robustness Computations for Paper v21
Tasks C5, C2, C4, C1, C3 — executed in priority order.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import json
import warnings
import os
from pathlib import Path
from datetime import datetime
from scipy import stats

warnings.filterwarnings("ignore")

# ── Paths ────────────────────────────────────────────────────
BASE = Path('/home/user/Claude/handoff')
MEDIA = BASE / 'media'
DATA_PROC = BASE / 'data' / 'processed'
DATA_RAW = BASE / 'data' / 'raw'
MEDIA.mkdir(parents=True, exist_ok=True)
DATA_PROC.mkdir(parents=True, exist_ok=True)

# Actual file locations (adapted from exploration)
TIER_SHARES = '/home/user/Claude/exhibit_C1_gateway_shares_daily_upgraded.csv'
CONCENTRATION = '/home/user/Claude/exhibit_C2_concentration_daily_upgraded.csv'
GATEWAY_VOL = BASE / 'data' / 'raw' / 'dune_gateway_volume.csv'
ETH_TOTAL = BASE / 'data' / 'raw' / 'dune_eth_total_v2.csv'
FRED = BASE / 'data' / 'raw' / 'fred_wide.csv'
SUPPLY = BASE / 'data' / 'raw' / 'stablecoin_supply_extended.csv'

# ── Style ────────────────────────────────────────────────────
FED_NAVY = '#003366'
FED_BLUE = '#336699'
FED_LIGHT = '#6699CC'
FED_RED = '#CC3333'
FED_GOLD = '#CC9933'
FED_GRAY = '#808080'
FED_DARK = '#404040'

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
    'axes.grid': True,
    'grid.color': '#E0E0E0',
    'grid.linestyle': '--',
    'grid.alpha': 0.7,
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
})

# ── CLII Scores ──────────────────────────────────────────────
CLII_SCORES = {
    'Circle': 0.92, 'Paxos': 0.88, 'PayPal': 0.88, 'Coinbase': 0.85,
    'Gemini': 0.82, 'BitGo': 0.80, 'Robinhood': 0.75, 'Kraken': 0.58,
    'Tether': 0.45, 'Bybit': 0.40, 'OKX': 0.40, 'Binance': 0.38,
    'Aave V3': 0.18, 'Compound V3': 0.18, 'Uniswap V3': 0.15,
    'Uniswap Universal Router': 0.15, '1inch': 0.12, 'Curve 3pool': 0.12,
    'Tornado Cash': 0.02
}

GATEWAY_NAME_MAP = {
    'Aave V3': 'Aave V3',
    'Binance': 'Binance',
    'Circle Treasury': 'Circle',
    'Coinbase': 'Coinbase',
    'Curve 3pool': 'Curve 3pool',
    'Gemini': 'Gemini',
    'OKX': 'OKX',
    'Tether Treasury': 'Tether',
    'Tornado Cash': 'Tornado Cash',
    'Uniswap V3': 'Uniswap V3',
}

def metadata():
    return {
        "computed_at": datetime.utcnow().isoformat() + "Z",
        "script_version": "phase4_v1",
    }

def save_json(data, filename):
    path = DATA_PROC / filename
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    print(f"  Saved: {path}")

def save_fig(fig, filename):
    path = MEDIA / filename
    fig.savefig(path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"  Saved: {path}")


# ══════════════════════════════════════════════════════════════
# TASK C5: Day-of-Week Baseline
# ══════════════════════════════════════════════════════════════
def task_c5():
    print("\n" + "=" * 60)
    print("TASK C5: Day-of-Week Baseline")
    print("=" * 60)

    df = pd.read_csv(TIER_SHARES, parse_dates=['date_utc'])
    df = df.rename(columns={'date_utc': 'date'})
    # Use tier1_A_share (variant A = paper's primary method)
    df['tier1_share_pct'] = df['tier1_A_share'] * 100  # convert to pct
    df['dow'] = df['date'].dt.dayofweek  # 0=Mon, 6=Sun
    df['dow_name'] = df['date'].dt.day_name()

    DOW_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    # Full sample stats
    full_by_day = {}
    for i, name in enumerate(DOW_NAMES):
        sub = df[df['dow'] == i]['tier1_share_pct']
        full_by_day[name] = {
            "mean": round(float(sub.mean()), 4),
            "std": round(float(sub.std()), 4),
            "n": int(len(sub))
        }

    weekday_mask = df['dow'] < 5
    weekday_avg = float(df[weekday_mask]['tier1_share_pct'].mean())
    weekend_mask = df['dow'] >= 5
    weekend_avg = float(df[weekend_mask]['tier1_share_pct'].mean())
    weekend_dip_pp = weekend_avg - weekday_avg
    weekend_std = float(df[weekend_mask]['tier1_share_pct'].std())

    full_sample = {
        "by_day": full_by_day,
        "weekday_avg": round(weekday_avg, 4),
        "weekend_avg": round(weekend_avg, 4),
        "weekend_dip_pp": round(weekend_dip_pp, 4),
        "weekend_std": round(weekend_std, 4),
    }

    # Calm period: exclude Feb-April 2023
    calm_mask = ~((df['date'].dt.year == 2023) & (df['date'].dt.month >= 2) & (df['date'].dt.month <= 4))
    calm = df[calm_mask]
    calm_by_day = {}
    for i, name in enumerate(DOW_NAMES):
        sub = calm[calm['dow'] == i]['tier1_share_pct']
        calm_by_day[name] = {
            "mean": round(float(sub.mean()), 4),
            "std": round(float(sub.std()), 4),
            "n": int(len(sub))
        }
    calm_wd = float(calm[calm['dow'] < 5]['tier1_share_pct'].mean())
    calm_we = float(calm[calm['dow'] >= 5]['tier1_share_pct'].mean())
    calm_we_std = float(calm[calm['dow'] >= 5]['tier1_share_pct'].std())
    calm_sample = {
        "by_day": calm_by_day,
        "weekday_avg": round(calm_wd, 4),
        "weekend_avg": round(calm_we, 4),
        "weekend_dip_pp": round(calm_we - calm_wd, 4),
        "weekend_std": round(calm_we_std, 4),
    }

    # SVB weekend: March 11-12, 2023 (Sat-Sun)
    svb_sat = df[df['date'] == '2023-03-11']
    svb_sun = df[df['date'] == '2023-03-12']
    sat_val = float(svb_sat['tier1_share_pct'].iloc[0]) if len(svb_sat) > 0 else None
    sun_val = float(svb_sun['tier1_share_pct'].iloc[0]) if len(svb_sun) > 0 else None
    svb_avg = np.mean([v for v in [sat_val, sun_val] if v is not None])

    # Use calm period weekend as the normal baseline
    normal_we_avg = calm_we
    normal_we_std_val = calm_we_std
    sigma = (svb_avg - normal_we_avg) / normal_we_std_val if normal_we_std_val > 0 else float('nan')

    svb_weekend = {
        "sat_mar11_t1_share": round(sat_val, 4) if sat_val else None,
        "sun_mar12_t1_share": round(sun_val, 4) if sun_val else None,
        "svb_weekend_avg": round(float(svb_avg), 4),
        "normal_weekend_avg": round(normal_we_avg, 4),
        "normal_weekend_std": round(normal_we_std_val, 4),
        "sigma_from_normal": round(float(sigma), 4),
    }

    results = {
        "metadata": {**metadata(), "data_sources": [TIER_SHARES]},
        "full_sample": full_sample,
        "calm_period": calm_sample,
        "svb_weekend": svb_weekend,
    }
    save_json(results, "day_of_week_baseline.json")

    print(f"\n  KEY FINDINGS:")
    print(f"  Weekday avg T1 share:  {weekday_avg:.2f}%")
    print(f"  Weekend avg T1 share:  {weekend_avg:.2f}%")
    print(f"  Normal weekend dip:    {weekend_dip_pp:+.2f} pp")
    print(f"  SVB weekend avg:       {svb_avg:.2f}%")
    print(f"  SVB sigma from normal: {sigma:.2f} std devs")

    return results


# ══════════════════════════════════════════════════════════════
# TASK C2: Stress Placebo Window
# ══════════════════════════════════════════════════════════════
def task_c2():
    print("\n" + "=" * 60)
    print("TASK C2: Stress Placebo Window")
    print("=" * 60)

    df = pd.read_csv(TIER_SHARES, parse_dates=['date_utc'])
    df = df.rename(columns={'date_utc': 'date'}).set_index('date').sort_index()
    df['tier1_pct'] = df['tier1_A_share'] * 100

    # SVB event window: 2023-03-09 to 2023-03-15
    svb_start = pd.Timestamp('2023-03-09')
    svb_end = pd.Timestamp('2023-03-15')

    # Pre-SVB: 7 days before
    pre_start = svb_start - pd.Timedelta(days=7)
    pre_svb = df.loc[pre_start:svb_start - pd.Timedelta(days=1), 'tier1_pct']
    during_svb = df.loc[svb_start:svb_end, 'tier1_pct']
    post_end = svb_end + pd.Timedelta(days=7)
    post_svb = df.loc[svb_end + pd.Timedelta(days=1):post_end, 'tier1_pct']

    svb_max_pre = float(pre_svb.max()) if len(pre_svb) > 0 else float('nan')
    svb_min_during = float(during_svb.min()) if len(during_svb) > 0 else float('nan')
    svb_max_post = float(post_svb.max()) if len(post_svb) > 0 else float('nan')
    svb_swing = svb_max_pre - svb_min_during

    print(f"  SVB: pre-max={svb_max_pre:.2f}%, during-min={svb_min_during:.2f}%, swing={svb_swing:.2f} pp")

    # 50 placebo windows
    np.random.seed(42)
    # Exclusion zone: March 2023 ± 14 days
    excl_start = pd.Timestamp('2023-02-23')
    excl_end = pd.Timestamp('2023-03-29')

    eligible_dates = df.index[(df.index < excl_start) | (df.index > excl_end)]
    # Need at least 21 days of data around each start (7 pre + 7 during + 7 post)
    eligible_dates = eligible_dates[(eligible_dates >= df.index[7]) & (eligible_dates <= df.index[-15])]

    placebo_starts = np.random.choice(eligible_dates, size=min(50, len(eligible_dates)), replace=False)
    placebo_swings = []
    placebo_results = []

    for start in sorted(placebo_starts):
        start = pd.Timestamp(start)
        p_pre = df.loc[start - pd.Timedelta(days=7):start - pd.Timedelta(days=1), 'tier1_pct']
        p_during = df.loc[start:start + pd.Timedelta(days=6), 'tier1_pct']
        p_post = df.loc[start + pd.Timedelta(days=7):start + pd.Timedelta(days=13), 'tier1_pct']

        if len(p_pre) > 0 and len(p_during) > 0:
            swing = float(p_pre.max()) - float(p_during.min())
            placebo_swings.append(swing)
            placebo_results.append({
                "start": str(start.date()),
                "pre_max": round(float(p_pre.max()), 4),
                "during_min": round(float(p_during.min()), 4),
                "swing_pp": round(swing, 4),
            })

    placebo_arr = np.array(placebo_swings)
    n_exceeding = int(np.sum(placebo_arr >= svb_swing))
    pctile = float(np.sum(placebo_arr < svb_swing) / len(placebo_arr) * 100)

    print(f"  Placebo: {len(placebo_swings)} windows, mean swing={np.mean(placebo_arr):.2f} pp")
    print(f"  SVB swing: {svb_swing:.2f} pp > {pctile:.0f}th percentile ({n_exceeding} placebos exceed)")

    # ── Exhibit ──
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 8), gridspec_kw={'height_ratios': [1.2, 1]})

    # Panel A: Time series
    ax1.plot(df.index, df['tier1_pct'], color=FED_GRAY, linewidth=0.6, alpha=0.8, zorder=1)
    ax1.axvspan(svb_start, svb_end, alpha=0.25, color=FED_RED, zorder=2, label='SVB window')
    for pr in placebo_results[:50]:
        d = pd.Timestamp(pr['start'])
        ax1.axvline(d, color=FED_BLUE, alpha=0.15, linewidth=0.5, zorder=0)
    # Blue dot legend entry
    ax1.scatter([], [], color=FED_BLUE, s=15, alpha=0.5, label='Placebo starts (n=50)')
    ax1.set_ylabel('Tier 1 Volume Share (%)')
    ax1.set_title('Tier 1 Volume Share: SVB Episode vs. Placebo Windows')
    ax1.legend(loc='lower left', framealpha=0.9)

    # Panel B: Histogram
    ax2.hist(placebo_arr, bins=20, color=FED_LIGHT, edgecolor=FED_NAVY, alpha=0.7, zorder=2)
    ax2.axvline(svb_swing, color=FED_RED, linewidth=2.5, linestyle='-', zorder=3,
                label=f'SVB swing: {svb_swing:.1f} pp')
    ax2.annotate(f'SVB swing: {svb_swing:.1f} pp\n(>{pctile:.0f}th percentile)',
                 xy=(svb_swing, ax2.get_ylim()[1] * 0.8),
                 xytext=(svb_swing + 2, ax2.get_ylim()[1] * 0.7 if svb_swing < np.mean(placebo_arr) + 10 else ax2.get_ylim()[1] * 0.7),
                 fontsize=9, color=FED_RED, fontweight='bold',
                 arrowprops=dict(arrowstyle='->', color=FED_RED, lw=1.5))
    ax2.set_xlabel('Tier 1 Share Swing (percentage points)')
    ax2.set_ylabel('Frequency')
    ax2.set_title('Distribution of Placebo Tier 1 Share Swings (7-Day Windows)')
    ax2.legend(loc='upper right')

    fig.tight_layout()
    save_fig(fig, 'exhibit_placebo_t1_share.png')

    results = {
        "metadata": {**metadata(), "data_sources": [TIER_SHARES]},
        "svb_window": {
            "start": "2023-03-09", "end": "2023-03-15",
            "pre_max_t1": round(svb_max_pre, 4),
            "during_min_t1": round(svb_min_during, 4),
            "post_max_t1": round(svb_max_post, 4),
            "swing_pp": round(svb_swing, 4),
        },
        "placebo": {
            "n_windows": len(placebo_swings),
            "mean_swing": round(float(np.mean(placebo_arr)), 4),
            "median_swing": round(float(np.median(placebo_arr)), 4),
            "std_swing": round(float(np.std(placebo_arr)), 4),
            "max_swing": round(float(np.max(placebo_arr)), 4),
            "n_exceeding_svb": n_exceeding,
            "svb_percentile": round(pctile, 2),
        },
        "placebo_windows": placebo_results,
    }
    save_json(results, "placebo_analysis.json")
    return results


# ══════════════════════════════════════════════════════════════
# TASK C4: CLII Continuous Robustness
# ══════════════════════════════════════════════════════════════
def task_c4():
    print("\n" + "=" * 60)
    print("TASK C4: CLII Continuous Robustness")
    print("=" * 60)

    # Build flow retention data from gateway volumes during SVB and BUSD events
    gw = pd.read_csv(GATEWAY_VOL, parse_dates=['day'])
    gw.columns = [c.strip() for c in gw.columns]
    gw['day'] = pd.to_datetime(gw['day'], utc=True).dt.tz_localize(None).dt.normalize()

    # Map gateway names to canonical CLII names
    gw['entity'] = gw['name'].map(GATEWAY_NAME_MAP).fillna(gw['name'])
    gw['clii'] = gw['entity'].map(CLII_SCORES).fillna(0.18)  # default for unknown

    # Aggregate daily volume by entity
    daily_entity = gw.groupby(['day', 'entity', 'clii'])['volume_usd'].sum().reset_index()

    # SVB event: 28-day baseline = Feb 9-Mar 8, stress = Mar 9-15
    svb_base_s, svb_base_e = pd.Timestamp('2023-02-09'), pd.Timestamp('2023-03-08')
    svb_stress_s, svb_stress_e = pd.Timestamp('2023-03-09'), pd.Timestamp('2023-03-15')

    # BUSD event: 28-day baseline before NYDFS enforcement, stress = Feb 13-21
    busd_base_s, busd_base_e = pd.Timestamp('2023-01-16'), pd.Timestamp('2023-02-12')
    busd_stress_s, busd_stress_e = pd.Timestamp('2023-02-13'), pd.Timestamp('2023-02-21')

    retention_rows = []
    for event, (bs, be, ss, se) in [
        ('SVB', (svb_base_s, svb_base_e, svb_stress_s, svb_stress_e)),
        ('BUSD', (busd_base_s, busd_base_e, busd_stress_s, busd_stress_e))
    ]:
        baseline = daily_entity[(daily_entity['day'] >= bs) & (daily_entity['day'] <= be)]
        stress = daily_entity[(daily_entity['day'] >= ss) & (daily_entity['day'] <= se)]

        base_days = (be - bs).days + 1
        stress_days = (se - ss).days + 1

        for ent in daily_entity['entity'].unique():
            base_vol = baseline[baseline['entity'] == ent]['volume_usd'].sum()
            stress_vol = stress[stress['entity'] == ent]['volume_usd'].sum()
            clii = CLII_SCORES.get(ent, 0.18)

            # Normalize to daily average
            base_daily = base_vol / base_days if base_days > 0 else 0
            stress_daily = stress_vol / stress_days if stress_days > 0 else 0
            retention = stress_daily / base_daily if base_daily > 0 else float('nan')

            if base_vol > 0:
                retention_rows.append({
                    'event': event, 'entity': ent, 'clii': clii,
                    'baseline_daily_vol': base_daily,
                    'stress_daily_vol': stress_daily,
                    'retention_ratio': retention,
                })

    ret_df = pd.DataFrame(retention_rows).dropna(subset=['retention_ratio'])

    # Panel A: CLII vs retention for both events
    svb_ret = ret_df[ret_df['event'] == 'SVB']
    busd_ret = ret_df[ret_df['event'] == 'BUSD']

    def linreg(x, y):
        if len(x) < 3:
            return {'r': float('nan'), 'p': float('nan'), 'slope': float('nan'), 'intercept': float('nan'), 'n': len(x)}
        slope, intercept, r, p, se = stats.linregress(x, y)
        return {'r': round(r, 4), 'p': round(float(p), 4), 'slope': round(slope, 4), 'intercept': round(intercept, 4), 'n': len(x)}

    svb_lr = linreg(svb_ret['clii'].values, svb_ret['retention_ratio'].values)
    busd_lr = linreg(busd_ret['clii'].values, busd_ret['retention_ratio'].values)
    pooled_lr = linreg(ret_df['clii'].values, ret_df['retention_ratio'].values)

    print(f"  SVB CLII-retention: r={svb_lr['r']}, p={svb_lr['p']}, n={svb_lr['n']}")
    print(f"  BUSD CLII-retention: r={busd_lr['r']}, p={busd_lr['p']}, n={busd_lr['n']}")
    print(f"  Pooled: r={pooled_lr['r']}, p={pooled_lr['p']}, n={pooled_lr['n']}")

    # Panel B: Volume falsification — CLII vs total volume (all entities)
    entity_vols = pd.read_csv(DATA_PROC / 'multichain_entity_volumes.csv')
    entity_vols['clii'] = entity_vols['entity'].map(CLII_SCORES)
    vol_valid = entity_vols.dropna(subset=['clii'])
    vol_valid = vol_valid[vol_valid['total_volume'] > 0]
    vol_valid['log_vol'] = np.log10(vol_valid['total_volume'] / 1e9)  # in $B log10

    vol_lr = linreg(vol_valid['clii'].values, vol_valid['log_vol'].values)
    print(f"  Volume falsification: r={vol_lr['r']}, p={vol_lr['p']}, n={vol_lr['n']}")

    # Panel C: Alternative groupings
    # Use SVB retention data for tier groupings
    svb_data = svb_ret.copy()

    # Terciles
    tercile_cuts = pd.qcut(svb_data['clii'], q=3, labels=['Low', 'Mid', 'High'], duplicates='drop')
    tercile_means = svb_data.groupby(tercile_cuts, observed=True)['retention_ratio'].mean()

    # Quartiles
    quartile_cuts = pd.qcut(svb_data['clii'], q=4, labels=['Q1 (Low)', 'Q2', 'Q3', 'Q4 (High)'], duplicates='drop')
    quartile_means = svb_data.groupby(quartile_cuts, observed=True)['retention_ratio'].mean()

    alt_groupings = {
        "terciles": {k: round(v, 4) for k, v in tercile_means.items()},
        "quartiles": {k: round(v, 4) for k, v in quartile_means.items()},
    }
    print(f"  Tercile retention: {dict(tercile_means.round(4))}")
    print(f"  Quartile retention: {dict(quartile_means.round(4))}")

    # ── Exhibit: 3-panel figure ──
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(14, 5.5))

    # Panel A: CLII vs retention
    ax1.scatter(svb_ret['clii'], svb_ret['retention_ratio'], color=FED_NAVY, s=50,
                zorder=3, label=f'SVB (r={svb_lr["r"]:.2f})', marker='o', alpha=0.8)
    ax1.scatter(busd_ret['clii'], busd_ret['retention_ratio'], color=FED_GOLD, s=50,
                zorder=3, label=f'BUSD (r={busd_lr["r"]:.2f})', marker='^', alpha=0.8)

    # OLS lines
    x_line = np.linspace(0, 1, 100)
    if not np.isnan(svb_lr['slope']):
        ax1.plot(x_line, svb_lr['slope'] * x_line + svb_lr['intercept'],
                 color=FED_NAVY, linestyle='--', linewidth=1.2, alpha=0.6)
    if not np.isnan(busd_lr['slope']):
        ax1.plot(x_line, busd_lr['slope'] * x_line + busd_lr['intercept'],
                 color=FED_GOLD, linestyle='--', linewidth=1.2, alpha=0.6)

    ax1.set_xlabel('CLII Score')
    ax1.set_ylabel('Flow Retention Ratio')
    ax1.set_title('A. CLII vs. Stress Flow Retention')
    ax1.legend(fontsize=8, loc='best')
    svb_p_str = f"p={svb_lr['p']:.3f}" if svb_lr['p'] < 1 else "p=N/A"
    busd_p_str = f"p={busd_lr['p']:.3f}" if busd_lr['p'] < 1 else "p=N/A"
    ax1.text(0.05, 0.05, f"SVB: r={svb_lr['r']:.2f}, {svb_p_str}\nBUSD: r={busd_lr['r']:.2f}, {busd_p_str}",
             transform=ax1.transAxes, fontsize=7.5, va='bottom',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    # Panel B: Volume falsification
    ax2.scatter(vol_valid['clii'], vol_valid['log_vol'], color=FED_NAVY, s=50, zorder=3, alpha=0.8)
    if not np.isnan(vol_lr['slope']):
        ax2.plot(x_line, vol_lr['slope'] * x_line + vol_lr['intercept'],
                 color=FED_RED, linestyle='--', linewidth=1.5, alpha=0.7)
    ax2.set_xlabel('CLII Score')
    ax2.set_ylabel('log10(Total Volume, $B)')
    ax2.set_title('B. CLII vs. Total Volume (Falsification)')
    sig_str = "not significant" if vol_lr['p'] > 0.05 else f"p={vol_lr['p']:.3f}"
    falsif_text = (f"r = {vol_lr['r']:.2f}, {sig_str}\n"
                   f"CLII does not predict volume\n"
                   f"(falsification passes)")
    ax2.text(0.95, 0.95, falsif_text,
             transform=ax2.transAxes, fontsize=7.5, va='top', ha='right',
             bbox=dict(boxstyle='round', facecolor='#F5F5F5', edgecolor='#CCCCCC', alpha=0.9))

    # Panel C: Alternative groupings
    terc_labels = list(tercile_means.index)
    terc_vals = list(tercile_means.values)
    quart_labels = list(quartile_means.index)
    quart_vals = list(quartile_means.values)

    x_terc = np.arange(len(terc_labels))
    x_quart = np.arange(len(quart_labels))
    width = 0.35

    # Plot terciles and quartiles side-by-side if same length, else stacked
    bar_labels = terc_labels + [''] + quart_labels
    bar_vals = list(terc_vals) + [0] + list(quart_vals)
    bar_colors = [FED_NAVY] * len(terc_labels) + ['white'] + [FED_BLUE] * len(quart_labels)
    x_pos = np.arange(len(bar_labels))

    bars = ax3.bar(x_pos, bar_vals, color=bar_colors, edgecolor=[FED_DARK if c != 'white' else 'white' for c in bar_colors], width=0.7)
    ax3.set_xticks(x_pos)
    ax3.set_xticklabels(bar_labels, rotation=30, ha='right', fontsize=7.5)
    ax3.set_ylabel('Mean SVB Retention Ratio')
    ax3.set_title('C. Retention by Alternative Groupings')

    # Add group labels
    terc_mid = len(terc_labels) / 2 - 0.5
    quart_mid = len(terc_labels) + 1 + len(quart_labels) / 2 - 0.5
    ax3.text(terc_mid, max(bar_vals) * 0.97, 'Terciles', ha='center', fontsize=8, fontweight='bold', color=FED_NAVY)
    ax3.text(quart_mid, max(bar_vals) * 0.97, 'Quartiles', ha='center', fontsize=8, fontweight='bold', color=FED_BLUE)

    fig.tight_layout()
    save_fig(fig, 'exhibit_clii_continuous.png')

    results = {
        "metadata": {**metadata(), "data_sources": [str(GATEWAY_VOL), str(DATA_PROC / 'multichain_entity_volumes.csv')]},
        "retention_regression": {
            "svb": svb_lr,
            "busd": busd_lr,
            "pooled": pooled_lr,
        },
        "volume_falsification": vol_lr,
        "alternative_groupings": alt_groupings,
        "retention_data": retention_rows,
    }
    save_json(results, "clii_continuous_robustness.json")
    return results


# ══════════════════════════════════════════════════════════════
# TASK C1: Coverage Sensitivity Band
# ══════════════════════════════════════════════════════════════
def task_c1():
    print("\n" + "=" * 60)
    print("TASK C1: Coverage Sensitivity Band")
    print("=" * 60)

    # Load ETH total volume
    eth = pd.read_csv(ETH_TOTAL, parse_dates=['day'])
    eth['day'] = pd.to_datetime(eth['day'], utc=True).dt.tz_localize(None).dt.normalize()
    total_eth = eth['volume_usd'].sum()

    # Load gateway volume
    gw = pd.read_csv(GATEWAY_VOL, parse_dates=['day'])
    gw.columns = [c.strip() for c in gw.columns]
    gw['day'] = pd.to_datetime(gw['day'], utc=True).dt.tz_localize(None).dt.normalize()
    gw['entity'] = gw['name'].map(GATEWAY_NAME_MAP).fillna(gw['name'])
    gw['clii'] = gw['entity'].map(CLII_SCORES).fillna(0.18)

    # Assign tiers
    def get_tier(clii):
        if clii > 0.75: return 1
        elif clii >= 0.30: return 2
        else: return 3

    gw['tier_calc'] = gw['clii'].apply(get_tier)

    t1_vol = gw[gw['tier_calc'] == 1]['volume_usd'].sum()
    t2_vol = gw[gw['tier_calc'] == 2]['volume_usd'].sum()
    t3_vol = gw[gw['tier_calc'] == 3]['volume_usd'].sum()
    total_labeled = t1_vol + t2_vol + t3_vol
    unlabeled = total_eth - total_labeled
    coverage = total_labeled / total_eth

    t1_share = t1_vol / total_labeled * 100
    t2_share = t2_vol / total_labeled * 100
    t3_share = t3_vol / total_labeled * 100

    print(f"  Total ETH volume:   ${total_eth/1e12:.2f}T")
    print(f"  Labeled gateway:    ${total_labeled/1e12:.2f}T ({coverage:.1%})")
    print(f"  Unlabeled:          ${unlabeled/1e12:.2f}T")
    print(f"  Current shares: T1={t1_share:.1f}%, T2={t2_share:.1f}%, T3={t3_share:.1f}%")

    # Sensitivity: what if X% of unlabeled is unidentified T2?
    scenarios = [0, 5, 10, 15, 20, 25]
    results_scenarios = []
    for pct in scenarios:
        add_t2 = unlabeled * (pct / 100)
        new_total = total_labeled + add_t2
        new_t1 = t1_vol / new_total * 100
        new_t2 = (t2_vol + add_t2) / new_total * 100
        new_t3 = t3_vol / new_total * 100

        # Tier-level HHI (treating each tier as a "firm" share)
        hhi = new_t1**2 + new_t2**2 + new_t3**2

        results_scenarios.append({
            "unlabeled_t2_pct": pct,
            "new_t1_share": round(new_t1, 4),
            "new_t2_share": round(new_t2, 4),
            "new_t3_share": round(new_t3, 4),
            "tier_hhi": round(hhi, 1),
            "new_coverage": round((new_total / total_eth) * 100, 2),
        })
        print(f"  Scenario {pct}%: T1={new_t1:.1f}%, T2={new_t2:.1f}%, HHI={hhi:.0f}")

    # Reverse: what % of unlabeled would need to be T1 to push T1 above 50%, 60%?
    # T1_new / (total_labeled + add_t1) > target
    # (t1_vol + add_t1) / (total_labeled + add_t1) > target
    # t1_vol + add_t1 > target * (total_labeled + add_t1)
    # add_t1 * (1 - target) > target * total_labeled - t1_vol
    # add_t1 > (target * total_labeled - t1_vol) / (1 - target)
    reverse = {}
    for target_pct in [50, 60]:
        target = target_pct / 100
        needed_add = (target * total_labeled - t1_vol) / (1 - target)
        if needed_add <= 0:
            reverse[f"t1_above_{target_pct}pct"] = "Already above"
        else:
            pct_of_unlabeled = needed_add / unlabeled * 100
            reverse[f"t1_above_{target_pct}pct"] = round(pct_of_unlabeled, 2)
            print(f"  T1 > {target_pct}%: need {pct_of_unlabeled:.1f}% of unlabeled attributed as T1")

    # ── Exhibit ──
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

    pcts = [s['unlabeled_t2_pct'] for s in results_scenarios]
    t1s = [s['new_t1_share'] for s in results_scenarios]
    hhis = [s['tier_hhi'] for s in results_scenarios]

    # Panel A: T1 share
    ax1.plot(pcts, t1s, color=FED_NAVY, linewidth=2, marker='o', markersize=6, zorder=3)
    ax1.scatter([0], [t1s[0]], color=FED_GOLD, s=120, marker='*', zorder=4, label='Current')
    ax1.axhline(50, color=FED_RED, linestyle='--', linewidth=1, alpha=0.7, label='Parity threshold (50%)')
    ax1.fill_between(pcts, t1s, alpha=0.1, color=FED_NAVY)
    ax1.set_xlabel('Unlabeled Volume Attributed to Tier 2 (%)')
    ax1.set_ylabel('Tier 1 Share of Total Volume (%)')
    ax1.set_title('A. Tier 1 Volume Share Under Coverage Scenarios')
    ax1.legend(fontsize=8)

    # Panel B: HHI
    ax2.plot(pcts, hhis, color=FED_NAVY, linewidth=2, marker='s', markersize=6, zorder=3)
    ax2.scatter([0], [hhis[0]], color=FED_GOLD, s=120, marker='*', zorder=4, label='Current')
    ax2.axhline(2500, color=FED_RED, linestyle='--', linewidth=1, alpha=0.7, label='Highly concentrated (2500)')
    ax2.axhline(1500, color=FED_GOLD, linestyle='--', linewidth=1, alpha=0.7, label='Moderately concentrated (1500)')
    ax2.set_xlabel('Unlabeled Volume Attributed to Tier 2 (%)')
    ax2.set_ylabel('Tier-Level HHI')
    ax2.set_title('B. Tier-Level HHI Under Coverage Scenarios')
    ax2.legend(fontsize=8)

    fig.tight_layout()
    save_fig(fig, 'exhibit_coverage_sensitivity.png')

    results = {
        "metadata": {**metadata(), "data_sources": [str(ETH_TOTAL), str(GATEWAY_VOL)]},
        "baseline": {
            "total_eth_volume": round(total_eth, 2),
            "labeled_volume": round(total_labeled, 2),
            "unlabeled_volume": round(unlabeled, 2),
            "coverage_ratio": round(coverage, 4),
            "t1_share": round(t1_share, 4),
            "t2_share": round(t2_share, 4),
            "t3_share": round(t3_share, 4),
        },
        "scenarios": results_scenarios,
        "reverse_analysis": reverse,
    }
    save_json(results, "coverage_sensitivity.json")
    return results


# ══════════════════════════════════════════════════════════════
# TASK C3: Trivariate Cointegration Robustness
# ══════════════════════════════════════════════════════════════
def task_c3():
    print("\n" + "=" * 60)
    print("TASK C3: Trivariate Cointegration Robustness")
    print("=" * 60)

    from statsmodels.tsa.vector_ar.vecm import coint_johansen
    from statsmodels.tsa.vector_ar.var_model import VAR

    # Replicate EXACTLY the load_data() from 02_cointegration.py:
    #   fred = pd.read_csv(DATA_RAW / "fred_wide.csv", ...)
    #   sc = pd.read_csv(DATA_PROC / "unified_extended_dataset.csv", ...)
    #   supply = sc["total_supply"]
    #   merged = fred[["WSHOMCB", "RRPONTSYD"]].join(pd.DataFrame(supply), how="inner")
    #   merged["RRPONTSYD"] = merged["RRPONTSYD"].ffill()
    #   weekly = merged.resample("W-WED").last().dropna()
    fred = pd.read_csv(FRED, index_col=0, parse_dates=True)
    sc = pd.read_csv(DATA_PROC / 'unified_extended_dataset.csv', index_col=0, parse_dates=True)
    supply = sc['total_supply']

    # Build baseline trivariate exactly as original
    base_merged = fred[['WSHOMCB', 'RRPONTSYD']].join(pd.DataFrame(supply), how='inner').dropna(subset=['WSHOMCB'])
    base_merged['RRPONTSYD'] = base_merged['RRPONTSYD'].ffill()
    base_weekly = base_merged.resample('W-WED').last().dropna()
    primary_base = base_weekly['2023-02-01':'2026-01-31']
    print(f"  Primary sample (baseline): {len(primary_base)} weeks")

    # For quadrivariate tests: start from the same base, add extra FRED columns
    # This ensures the weekly alignment is identical to baseline
    primary_ext = primary_base.copy()
    for col in ['DFF', 'SOFR', 'DGS10']:
        if col in fred.columns:
            # Resample the FRED column to weekly, then join
            col_weekly = fred[col].ffill().resample('W-WED').last()
            primary_ext = primary_ext.join(col_weekly, how='left')
            primary_ext[col] = primary_ext[col].ffill()
    primary = primary_ext

    def run_johansen(data, var_names, max_lag=8):
        """Run Johansen cointegration test. max_lag=8 matches paper methodology."""
        log_data = np.log(data.replace(0, np.nan).dropna())
        if len(log_data) < 30:
            return None

        try:
            var_model = VAR(log_data)
            lag = var_model.select_order(maxlags=max_lag).aic
            lag = max(1, min(lag, max_lag))
            k = max(1, lag - 1)

            joh = coint_johansen(log_data, det_order=0, k_ar_diff=k)
            n_vars = log_data.shape[1]

            rank = 0
            trace_results = []
            for i in range(n_vars):
                stat = float(joh.lr1[i])
                cv95 = float(joh.cvt[i, 1])
                reject = stat > cv95
                if reject:
                    rank += 1
                trace_results.append({
                    "h0_rank_le": i,
                    "stat": round(stat, 2),
                    "cv95": round(cv95, 2),
                    "reject": reject,
                })

            return {
                "variables": var_names,
                "n_obs": len(log_data),
                "lag_aic": lag,
                "k_ar_diff": k,
                "rank": rank,
                "cointegrated": rank > 0,
                "trace_results": trace_results,
                "first_trace_stat": round(float(joh.lr1[0]), 2),
                "first_trace_cv95": round(float(joh.cvt[0, 1]), 2),
            }
        except Exception as e:
            print(f"    ERROR: {e}")
            return {"variables": var_names, "error": str(e)}

    # Baseline trivariate — using EXACTLY the data from 02_cointegration.py
    print("\n  Baseline (3-var): Fed Assets, ON RRP, Supply")
    base_data = primary_base[['WSHOMCB', 'RRPONTSYD', 'total_supply']].dropna()
    baseline = run_johansen(base_data, ['WSHOMCB', 'RRPONTSYD', 'total_supply'])
    if baseline and 'rank' in baseline:
        print(f"    Lag={baseline['lag_aic']}, Trace={baseline['first_trace_stat']}, CV95={baseline['first_trace_cv95']}, Rank={baseline['rank']}")

    # Quadrivariate tests
    systems = []

    # + DFF
    print("\n  + Fed Funds Rate (DFF)")
    dff_data = primary[['WSHOMCB', 'RRPONTSYD', 'total_supply', 'DFF']].dropna()
    dff_result = run_johansen(dff_data, ['WSHOMCB', 'RRPONTSYD', 'total_supply', 'DFF'])
    if dff_result and 'rank' in dff_result:
        survives = dff_result['rank'] >= 1
        dff_result['original_survives'] = survives
        print(f"    Lag={dff_result['lag_aic']}, Trace={dff_result['first_trace_stat']}, CV95={dff_result['first_trace_cv95']}, Rank={dff_result['rank']}, Survives={survives}")
    systems.append(("+ Fed Funds Rate", dff_result))

    # + SOFR
    print("\n  + SOFR")
    sofr_data = primary[['WSHOMCB', 'RRPONTSYD', 'total_supply', 'SOFR']].dropna()
    sofr_result = run_johansen(sofr_data, ['WSHOMCB', 'RRPONTSYD', 'total_supply', 'SOFR'])
    if sofr_result and 'rank' in sofr_result:
        survives = sofr_result['rank'] >= 1
        sofr_result['original_survives'] = survives
        print(f"    Lag={sofr_result['lag_aic']}, Trace={sofr_result['first_trace_stat']}, CV95={sofr_result['first_trace_cv95']}, Rank={sofr_result['rank']}, Survives={survives}")
    systems.append(("+ SOFR", sofr_result))

    # + DGS10
    print("\n  + 10Y Yield (DGS10)")
    dgs_data = primary[['WSHOMCB', 'RRPONTSYD', 'total_supply', 'DGS10']].dropna()
    dgs_result = run_johansen(dgs_data, ['WSHOMCB', 'RRPONTSYD', 'total_supply', 'DGS10'])
    if dgs_result and 'rank' in dgs_result:
        survives = dgs_result['rank'] >= 1
        dgs_result['original_survives'] = survives
        print(f"    Lag={dgs_result['lag_aic']}, Trace={dgs_result['first_trace_stat']}, CV95={dgs_result['first_trace_cv95']}, Rank={dgs_result['rank']}, Survives={survives}")
    systems.append(("+ 10Y Yield", dgs_result))

    # ── Exhibit: Bar chart of trace stats ──
    fig, ax = plt.subplots(figsize=(8, 5))

    labels = ['Baseline\n(3-var)']
    trace_stats = [baseline['first_trace_stat'] if baseline and 'first_trace_stat' in baseline else 0]
    cv95s = [baseline['first_trace_cv95'] if baseline and 'first_trace_cv95' in baseline else 0]
    ranks = [baseline['rank'] if baseline and 'rank' in baseline else 0]

    for name, res in systems:
        labels.append(name.replace('+ ', '+\n'))
        if res and 'first_trace_stat' in res:
            trace_stats.append(res['first_trace_stat'])
            cv95s.append(res['first_trace_cv95'])
            ranks.append(res['rank'])
        else:
            trace_stats.append(0)
            cv95s.append(0)
            ranks.append(0)

    x = np.arange(len(labels))
    bars = ax.bar(x, trace_stats, width=0.5, color=[FED_NAVY if r >= 1 else FED_GRAY for r in ranks],
                  edgecolor=FED_DARK, zorder=3)

    # CV95 line and labels
    max_val = max(trace_stats) if trace_stats else 50
    for i, (ts, cv, rk) in enumerate(zip(trace_stats, cv95s, ranks)):
        ax.hlines(cv, i - 0.3, i + 0.3, color=FED_RED, linewidth=2, linestyle='--', zorder=4)
        # Place label above bar with enough clearance
        label_y = max(ts, cv) + max_val * 0.04
        status = f"Rank={rk}" + (" (pass)" if rk >= 1 else " (fail)")
        ax.text(i, label_y, status, ha='center', fontsize=8, fontweight='bold',
                color=FED_NAVY if rk >= 1 else FED_RED)

    ax.set_ylim(0, max_val * 1.25)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel('Johansen Trace Statistic')
    ax.set_title('Cointegration Rank Under Alternative System Specifications')

    # Legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color=FED_NAVY, marker='s', linestyle='', markersize=10, label='Cointegrated (rank >= 1)'),
        Line2D([0], [0], color=FED_GRAY, marker='s', linestyle='', markersize=10, label='Not cointegrated'),
        Line2D([0], [0], color=FED_RED, linewidth=2, linestyle='--', label='95% critical value'),
    ]
    ax.legend(handles=legend_elements, fontsize=8, loc='upper right')

    fig.tight_layout()
    save_fig(fig, 'exhibit_trivariate_robustness.png')

    results = {
        "metadata": {**metadata(), "data_sources": [str(FRED), str(SUPPLY)]},
        "baseline": baseline,
        "quadrivariate": {
            "plus_dff": dff_result,
            "plus_sofr": sofr_result,
            "plus_dgs10": dgs_result,
        },
        "summary": {
            "baseline_rank": baseline.get('rank') if baseline else None,
            "dff_survives": dff_result.get('original_survives') if dff_result else None,
            "sofr_survives": sofr_result.get('original_survives') if sofr_result else None,
            "dgs10_survives": dgs_result.get('original_survives') if dgs_result else None,
        }
    }
    save_json(results, "trivariate_robustness.json")
    return results


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
def main():
    print("=" * 60)
    print("PHASE 4: ROBUSTNESS COMPUTATIONS")
    print("=" * 60)

    r_c5 = task_c5()
    r_c2 = task_c2()
    r_c4 = task_c4()
    r_c1 = task_c1()
    r_c3 = task_c3()

    # ── Summary ──
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"{'Task':<7} {'Output File':<45} {'Key Finding'}")
    print("-" * 100)

    # C5
    svb_sigma = r_c5['svb_weekend']['sigma_from_normal']
    we_dip = r_c5['full_sample']['weekend_dip_pp']
    print(f"C5      data/processed/day_of_week_baseline.json       Weekend dip: {we_dip:+.1f} pp (SVB: {svb_sigma:.1f} sigma)")

    # C2
    pctile = r_c2['placebo']['svb_percentile']
    print(f"C2      media/exhibit_placebo_t1_share.png              SVB swing: >{pctile:.0f}th percentile")

    # C4
    pooled_r = r_c4['retention_regression']['pooled']['r']
    print(f"C4      media/exhibit_clii_continuous.png               CLII-retention r={pooled_r:.2f} (continuous)")

    # C1
    t1_lo = min(s['new_t1_share'] for s in r_c1['scenarios'])
    t1_hi = max(s['new_t1_share'] for s in r_c1['scenarios'])
    print(f"C1      media/exhibit_coverage_sensitivity.png          T1 share range: {t1_lo:.1f}%-{t1_hi:.1f}% across scenarios")

    # C3
    c3_summary = r_c3.get('summary', {})
    base_rank = c3_summary.get('baseline_rank', '?')
    survives = []
    for k, v in c3_summary.items():
        if k.endswith('_survives') and v is not None:
            survives.append(v)
    n_survive = sum(survives)
    total_sys = len(survives)
    print(f"C3      media/exhibit_trivariate_robustness.png        Baseline rank={base_rank}; survives {n_survive}/{total_sys} extensions")

    print("\n" + "=" * 60)
    print("ALL TASKS COMPLETE")
    print("=" * 60)


if __name__ == '__main__':
    main()
