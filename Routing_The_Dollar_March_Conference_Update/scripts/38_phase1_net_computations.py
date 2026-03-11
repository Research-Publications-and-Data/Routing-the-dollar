"""38_phase1_net_computations.py — Net-of-internal HHI, tier correlations, flow retention.

Phase 1 of paper v18 revisions:
  Task 1: Net-of-Internal HHI Time Series
  Task 2: Net-of-Internal Tier Correlations with Fed Assets (WSHOMCB)
  Task 3: Flow Retention vs CLII Correlation — Verify Pooled Value
"""
import pandas as pd
import numpy as np
import json
import sys
from pathlib import Path
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROC = ROOT / "data" / "processed"

# ── Internal transfer deduction rates ────────────────────────
INTERNAL_RATES = {
    "Binance": 0.1834,
    "OKX": 0.1084,
    # Kraken 0.69% and Coinbase 0.00% are immaterial — no deduction
}

# ── CLII scores ──────────────────────────────────────────────
CLII = {
    "Circle": 0.92, "Paxos": 0.88, "Coinbase": 0.85, "Gemini": 0.82, "BitGo": 0.80,
    "Tether": 0.45, "Binance": 0.38, "Kraken": 0.42, "OKX": 0.40, "Bybit": 0.38,
    "Robinhood": 0.38,
    "Curve 3pool": 0.18, "1inch": 0.18, "Uniswap V3": 0.12, "Uniswap Universal Router": 0.12,
    "Compound V3": 0.15, "Aave V3": 0.10, "Tornado Cash": 0.02,
}


def load_daily():
    """Load and parse daily gateway data."""
    df = pd.read_csv(DATA_RAW / "dune_eth_daily_expanded_v2.csv")
    df["day"] = pd.to_datetime(df["day"], utc=True).dt.tz_localize(None)
    return df


def load_fred():
    """Load FRED wide data, extract WSHOMCB."""
    fred = pd.read_csv(DATA_RAW / "fred_wide.csv", index_col=0, parse_dates=True)
    wshomcb = fred[["WSHOMCB"]].dropna()
    return wshomcb


def compute_hhi(shares_series):
    """HHI from a series of shares (as fractions, not percentages)."""
    return float((shares_series ** 2).sum() * 10000)


def save_json(data, filename):
    path = DATA_PROC / filename
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"  Saved: {path}")


# ══════════════════════════════════════════════════════════════
# TASK 1: Net-of-Internal HHI Time Series
# ══════════════════════════════════════════════════════════════

def task1_net_hhi():
    print("\n" + "=" * 70)
    print("TASK 1: NET-OF-INTERNAL HHI TIME SERIES")
    print("=" * 70)

    df = load_daily()

    # Step 1: Daily entity gross volumes
    daily_entity = df.groupby(["day", "entity", "tier"])["volume_usd"].sum().reset_index()

    # Step 2: Apply internal transfer deductions
    daily_entity["net_volume_usd"] = daily_entity.apply(
        lambda r: r["volume_usd"] * (1 - INTERNAL_RATES.get(r["entity"], 0)),
        axis=1
    )

    # Step 3: Compute HHI for each day — both gross and net
    days = sorted(daily_entity["day"].unique())
    records = []

    for day in days:
        day_data = daily_entity[daily_entity["day"] == day]

        # --- Entity-level HHI ---
        gross_total = day_data["volume_usd"].sum()
        net_total = day_data["net_volume_usd"].sum()
        if gross_total == 0 or net_total == 0:
            continue

        gross_shares = day_data.groupby("entity")["volume_usd"].sum() / gross_total
        net_shares = day_data.groupby("entity")["net_volume_usd"].sum() / net_total

        entity_hhi_gross = compute_hhi(gross_shares)
        entity_hhi_net = compute_hhi(net_shares)

        # --- Tier-level HHI ---
        gross_tier = day_data.groupby("tier")["volume_usd"].sum()
        net_tier = day_data.groupby("tier")["net_volume_usd"].sum()

        gross_tier_shares = gross_tier / gross_tier.sum()
        net_tier_shares = net_tier / net_tier.sum()

        tier_hhi_gross = compute_hhi(gross_tier_shares)
        tier_hhi_net = compute_hhi(net_tier_shares)

        records.append({
            "day": day,
            "entity_hhi_gross": entity_hhi_gross,
            "entity_hhi_net": entity_hhi_net,
            "tier_hhi_gross": tier_hhi_gross,
            "tier_hhi_net": tier_hhi_net,
            "gross_t1": gross_tier.get(1, 0),
            "gross_t2": gross_tier.get(2, 0),
            "gross_t3": gross_tier.get(3, 0),
            "net_t1": net_tier.get(1, 0),
            "net_t2": net_tier.get(2, 0),
            "net_t3": net_tier.get(3, 0),
        })

    hhi_df = pd.DataFrame(records)

    # Step 4: Summary statistics
    def hhi_stats(series, label):
        return {
            "mean": round(float(series.mean()), 1),
            "median": round(float(series.median()), 1),
            "std": round(float(series.std()), 1),
            "min": round(float(series.min()), 1),
            "max": round(float(series.max()), 1),
            "pct_above_2500": round(float((series > 2500).mean() * 100), 1),
            "n_days": int(len(series)),
        }

    entity_gross_stats = hhi_stats(hhi_df["entity_hhi_gross"], "Entity HHI Gross")
    entity_net_stats = hhi_stats(hhi_df["entity_hhi_net"], "Entity HHI Net")
    tier_gross_stats = hhi_stats(hhi_df["tier_hhi_gross"], "Tier HHI Gross")
    tier_net_stats = hhi_stats(hhi_df["tier_hhi_net"], "Tier HHI Net")

    # Step 5: Aggregate tier shares
    total_gross = hhi_df[["gross_t1", "gross_t2", "gross_t3"]].sum()
    total_net = hhi_df[["net_t1", "net_t2", "net_t3"]].sum()
    gross_share_t1 = round(float(total_gross["gross_t1"] / total_gross.sum() * 100), 1)
    gross_share_t2 = round(float(total_gross["gross_t2"] / total_gross.sum() * 100), 1)
    gross_share_t3 = round(float(total_gross["gross_t3"] / total_gross.sum() * 100), 1)
    net_share_t1 = round(float(total_net["net_t1"] / total_net.sum() * 100), 1)
    net_share_t2 = round(float(total_net["net_t2"] / total_net.sum() * 100), 1)
    net_share_t3 = round(float(total_net["net_t3"] / total_net.sum() * 100), 1)

    # Step 6: Entity shares (net, full period aggregate)
    entity_net_totals = daily_entity.groupby("entity")["net_volume_usd"].sum()
    entity_net_shares = (entity_net_totals / entity_net_totals.sum() * 100).round(2)
    entity_shares_dict = entity_net_shares.sort_values(ascending=False).to_dict()

    # Step 7: Key determination — does net HHI fall below 2500?
    net_below_2500 = entity_net_stats["mean"] < 2500
    if net_below_2500:
        paper_impact = (
            f"NET entity HHI mean ({entity_net_stats['mean']:.0f}) falls BELOW the DOJ/FTC 2,500 threshold. "
            f"The paper's claim that gateway concentration is 'above the DOJ/FTC threshold' needs revision. "
            f"Suggested text: 'Gross entity HHI averages {entity_gross_stats['mean']:.0f} (above DOJ threshold "
            f"on {entity_gross_stats['pct_above_2500']:.0f}% of days), though after netting internal wallet "
            f"rebalancing the mean falls to {entity_net_stats['mean']:.0f} ({entity_net_stats['pct_above_2500']:.0f}% "
            f"of days above threshold).'"
        )
    else:
        paper_impact = (
            f"NET entity HHI mean ({entity_net_stats['mean']:.0f}) remains ABOVE the DOJ/FTC 2,500 threshold "
            f"(above on {entity_net_stats['pct_above_2500']:.0f}% of days vs. gross {entity_gross_stats['pct_above_2500']:.0f}%). "
            f"The paper's concentration claim holds. Recommend adding a footnote: 'Results are robust to netting "
            f"intra-entity wallet rebalancing (net HHI mean = {entity_net_stats['mean']:.0f}).'"
        )

    result = {
        "entity_hhi": {
            "gross": entity_gross_stats,
            "net": entity_net_stats,
            "delta_mean": round(entity_net_stats["mean"] - entity_gross_stats["mean"], 1),
        },
        "tier_hhi": {
            "gross": tier_gross_stats,
            "net": tier_net_stats,
            "delta_mean": round(tier_net_stats["mean"] - tier_gross_stats["mean"], 1),
        },
        "tier_shares": {
            "gross": {"T1": gross_share_t1, "T2": gross_share_t2, "T3": gross_share_t3},
            "net": {"T1": net_share_t1, "T2": net_share_t2, "T3": net_share_t3},
        },
        "entity_shares_net": entity_shares_dict,
        "caveat": (
            "Internal transfer rates applied as uniform daily deductions from sample-wide averages. "
            "Actual daily internal transfer rates vary. Binance: 18.34%, OKX: 10.84%. "
            "Kraken (0.69%) and Coinbase (0.00%) not deducted (immaterial)."
        ),
        "paper_impact": paper_impact,
        "net_below_2500": net_below_2500,
    }

    save_json(result, "hhi_net_of_internal.json")

    # Print summary
    print(f"\n  Entity HHI:  gross mean = {entity_gross_stats['mean']:.0f}  →  net mean = {entity_net_stats['mean']:.0f}  (Δ = {result['entity_hhi']['delta_mean']:+.0f})")
    print(f"  Above DOJ:   gross {entity_gross_stats['pct_above_2500']:.1f}%         →  net {entity_net_stats['pct_above_2500']:.1f}%")
    print(f"  Tier HHI:    gross mean = {tier_gross_stats['mean']:.0f}  →  net mean = {tier_net_stats['mean']:.0f}  (Δ = {result['tier_hhi']['delta_mean']:+.0f})")
    print(f"  Tier shares: gross T1/T2/T3 = {gross_share_t1}/{gross_share_t2}/{gross_share_t3}  →  net = {net_share_t1}/{net_share_t2}/{net_share_t3}")
    print(f"\n  PAPER IMPACT: {'NET BELOW 2500 — NEEDS REVISION' if net_below_2500 else 'Net still above 2500 — claim holds'}")
    print(f"  {paper_impact}")

    return result, hhi_df


# ══════════════════════════════════════════════════════════════
# TASK 2: Net-of-Internal Tier Correlations with Fed Assets
# ══════════════════════════════════════════════════════════════

def task2_tier_correlations():
    print("\n" + "=" * 70)
    print("TASK 2: NET-OF-INTERNAL TIER CORRELATIONS WITH FED ASSETS")
    print("=" * 70)

    df = load_daily()

    # Step 1: Daily tier volumes (gross and net)
    df["net_volume_usd"] = df.apply(
        lambda r: r["volume_usd"] * (1 - INTERNAL_RATES.get(r["entity"], 0)),
        axis=1
    )

    daily_tier_gross = df.groupby(["day", "tier"])["volume_usd"].sum().unstack(fill_value=0)
    daily_tier_net = df.groupby(["day", "tier"])["net_volume_usd"].sum().unstack(fill_value=0)

    daily_tier_gross.columns = [f"T{int(c)}" for c in daily_tier_gross.columns]
    daily_tier_net.columns = [f"T{int(c)}" for c in daily_tier_net.columns]

    # Step 2: Resample to Wednesday-to-Tuesday weeks (W-WED = weeks ending Wednesday)
    # FRED reports WSHOMCB on Wednesdays. Use W-WED to align.
    weekly_gross = daily_tier_gross.resample("W-WED").sum()
    weekly_net = daily_tier_net.resample("W-WED").sum()

    # Step 3: Load FRED WSHOMCB
    wshomcb = load_fred()
    # WSHOMCB is weekly, reported on Wednesdays. Resample to W-WED and forward-fill.
    wshomcb_weekly = wshomcb.resample("W-WED").last().ffill()

    # Step 4: Merge
    merged_gross = weekly_gross.join(wshomcb_weekly, how="inner").dropna(subset=["WSHOMCB"])
    merged_net = weekly_net.join(wshomcb_weekly, how="inner").dropna(subset=["WSHOMCB"])

    print(f"  Merged weeks (gross): {len(merged_gross)}")
    print(f"  Merged weeks (net): {len(merged_net)}")
    print(f"  Date range: {merged_gross.index[0].date()} to {merged_gross.index[-1].date()}")

    # Step 5: Correlations
    result = {"weekly_gross": {}, "weekly_net": {}, "delta": {}}

    for tier in ["T1", "T2", "T3"]:
        # Gross
        r_g, p_g = stats.pearsonr(merged_gross[tier], merged_gross["WSHOMCB"])
        result["weekly_gross"][tier] = {
            "r": round(float(r_g), 4),
            "p": round(float(p_g), 4),
            "n": int(len(merged_gross)),
        }

        # Net
        r_n, p_n = stats.pearsonr(merged_net[tier], merged_net["WSHOMCB"])
        result["weekly_net"][tier] = {
            "r": round(float(r_n), 4),
            "p": round(float(p_n), 4),
            "n": int(len(merged_net)),
        }

        result["delta"][f"{tier}_r"] = round(float(r_n - r_g), 4)

        sig_g = "***" if p_g < 0.001 else "**" if p_g < 0.01 else "*" if p_g < 0.05 else ""
        sig_n = "***" if p_n < 0.001 else "**" if p_n < 0.01 else "*" if p_n < 0.05 else ""
        print(f"\n  {tier}:")
        print(f"    Gross: r = {r_g:+.4f}{sig_g} (p = {p_g:.4f}, n = {len(merged_gross)})")
        print(f"    Net:   r = {r_n:+.4f}{sig_n} (p = {p_n:.4f}, n = {len(merged_net)})")
        print(f"    Delta: {r_n - r_g:+.4f}")

    result["note"] = (
        "Weekly frequency (W-WED, aligned to FRED Wednesday reporting). "
        "Paper reports earlier correlations at different frequencies "
        "(T1: -0.44, T2: +0.10, T3: +0.88). Weekly recomputation may differ slightly."
    )

    # Key question: T2 change
    t2_gross_r = result["weekly_gross"]["T2"]["r"]
    t2_net_r = result["weekly_net"]["T2"]["r"]
    t2_net_p = result["weekly_net"]["T2"]["p"]
    t2_changed = abs(t2_net_r - t2_gross_r) > 0.05

    if t2_changed and t2_net_r < -0.10 and t2_net_p < 0.05:
        result["paper_impact_T2"] = (
            f"T2 net correlation ({t2_net_r:+.4f}) is materially different from gross ({t2_gross_r:+.4f}) "
            f"and is significantly negative. The 'offshore exchanges uncorrelated with policy' "
            f"narrative needs revision."
        )
    elif t2_changed:
        result["paper_impact_T2"] = (
            f"T2 net correlation ({t2_net_r:+.4f}) differs from gross ({t2_gross_r:+.4f}) by {t2_net_r - t2_gross_r:+.4f}, "
            f"but the change does not fundamentally alter the narrative. Note the shift in a footnote."
        )
    else:
        result["paper_impact_T2"] = (
            f"T2 net correlation ({t2_net_r:+.4f}) is essentially unchanged from gross ({t2_gross_r:+.4f}). "
            f"The 'offshore exchanges uncorrelated with policy' narrative holds."
        )

    print(f"\n  PAPER IMPACT (T2): {result['paper_impact_T2']}")

    save_json(result, "tier_correlations_net.json")
    return result


# ══════════════════════════════════════════════════════════════
# TASK 3: Flow Retention vs CLII Correlation — Verify Pooled
# ══════════════════════════════════════════════════════════════

def task3_flow_retention():
    print("\n" + "=" * 70)
    print("TASK 3: FLOW RETENTION VS CLII — VERIFY POOLED VALUE")
    print("=" * 70)

    df = load_daily()

    # ── Step A: SVB-only ──
    print("\n  Step A: SVB crisis (Mar 9–15, 2023)")

    svb_baseline_start = pd.Timestamp("2023-02-09")
    svb_baseline_end = pd.Timestamp("2023-03-08")
    svb_stress_start = pd.Timestamp("2023-03-09")
    svb_stress_end = pd.Timestamp("2023-03-15")

    baseline_svb = df[(df["day"] >= svb_baseline_start) & (df["day"] <= svb_baseline_end)]
    stress_svb = df[(df["day"] >= svb_stress_start) & (df["day"] <= svb_stress_end)]

    baseline_avg_svb = baseline_svb.groupby("entity")["volume_usd"].sum() / \
        baseline_svb["day"].nunique()
    stress_avg_svb = stress_svb.groupby("entity")["volume_usd"].sum() / \
        stress_svb["day"].nunique()

    # Combine into retention ratios
    svb_entities = set(baseline_avg_svb.index) & set(stress_avg_svb.index)
    svb_data = []
    for entity in sorted(svb_entities):
        b = baseline_avg_svb.get(entity, 0)
        s = stress_avg_svb.get(entity, 0)
        clii = CLII.get(entity)
        if clii is None:
            continue
        if b < 1e6:  # Skip entities with negligible baseline (< $1M/day)
            print(f"    Skipping {entity}: baseline avg ${b/1e6:.2f}M/day (< $1M threshold)")
            continue
        retention = s / b if b > 0 else 0
        svb_data.append({"entity": entity, "clii": clii, "retention": retention,
                         "baseline_avg": b, "stress_avg": s})
        print(f"    {entity}: baseline ${b/1e6:.1f}M/day → stress ${s/1e6:.1f}M/day → retention {retention:.3f}")

    svb_df = pd.DataFrame(svb_data)
    if len(svb_df) >= 3:
        r_svb, p_svb = stats.pearsonr(svb_df["clii"], svb_df["retention"])
    else:
        r_svb, p_svb = float("nan"), float("nan")
    n_svb = len(svb_df)

    print(f"\n    SVB: r = {r_svb:.4f}, p = {p_svb:.4f}, n = {n_svb}")

    # ── Step B: BUSD wind-down ──
    print("\n  Step B: BUSD wind-down (Feb 13–19, 2023)")

    busd_baseline_start = pd.Timestamp("2023-02-06")
    busd_baseline_end = pd.Timestamp("2023-02-12")
    busd_stress_start = pd.Timestamp("2023-02-13")
    busd_stress_end = pd.Timestamp("2023-02-19")

    baseline_busd = df[(df["day"] >= busd_baseline_start) & (df["day"] <= busd_baseline_end)]
    stress_busd = df[(df["day"] >= busd_stress_start) & (df["day"] <= busd_stress_end)]

    baseline_avg_busd = baseline_busd.groupby("entity")["volume_usd"].sum() / \
        baseline_busd["day"].nunique()
    stress_avg_busd = stress_busd.groupby("entity")["volume_usd"].sum() / \
        stress_busd["day"].nunique()

    busd_entities = set(baseline_avg_busd.index) & set(stress_avg_busd.index)
    busd_data = []
    for entity in sorted(busd_entities):
        b = baseline_avg_busd.get(entity, 0)
        s = stress_avg_busd.get(entity, 0)
        clii = CLII.get(entity)
        if clii is None:
            continue
        if b < 1e6:
            print(f"    Skipping {entity}: baseline avg ${b/1e6:.2f}M/day (< $1M threshold)")
            continue
        retention = s / b if b > 0 else 0
        busd_data.append({"entity": entity, "clii": clii, "retention": retention,
                          "baseline_avg": b, "stress_avg": s})
        print(f"    {entity}: baseline ${b/1e6:.1f}M/day → stress ${s/1e6:.1f}M/day → retention {retention:.3f}")

    busd_df = pd.DataFrame(busd_data)
    if len(busd_df) >= 3:
        r_busd, p_busd = stats.pearsonr(busd_df["clii"], busd_df["retention"])
    else:
        r_busd, p_busd = float("nan"), float("nan")
    n_busd = len(busd_df)

    print(f"\n    BUSD: r = {r_busd:.4f}, p = {p_busd:.4f}, n = {n_busd}")

    # ── Step C: Pooled ──
    print("\n  Step C: Pooled (SVB + BUSD)")

    # Stack: each entity appears once per event
    pooled_rows = []
    for _, row in svb_df.iterrows():
        pooled_rows.append({"event": "svb", "entity": row["entity"],
                            "clii": row["clii"], "retention": row["retention"]})
    for _, row in busd_df.iterrows():
        pooled_rows.append({"event": "busd", "entity": row["entity"],
                            "clii": row["clii"], "retention": row["retention"]})

    pooled_df = pd.DataFrame(pooled_rows)
    n_pooled = len(pooled_df)

    if n_pooled >= 3:
        r_pooled, p_pooled = stats.pearsonr(pooled_df["clii"], pooled_df["retention"])
    else:
        r_pooled, p_pooled = float("nan"), float("nan")

    print(f"    Pooled: r = {r_pooled:.4f}, p = {p_pooled:.4f}, n = {n_pooled}")
    print(f"    SVB entities: {sorted(svb_df['entity'].tolist())}")
    print(f"    BUSD entities: {sorted(busd_df['entity'].tolist())}")

    # ── Diagnosis ──
    if abs(r_pooled - r_svb) < 0.01 and n_pooled > n_svb:
        diagnosis = (
            f"Pooled r ({r_pooled:.4f}) is nearly identical to SVB-only r ({r_svb:.4f}) despite "
            f"doubling the sample from n={n_svb} to n={n_pooled}. This occurs because "
            f"the BUSD event shows a similar CLII-retention pattern to SVB (BUSD r = {r_busd:.4f}). "
            f"The identical r is not an error — it reflects that both stress events produce "
            f"consistent patterns. However, the paper should note that pooling does not "
            f"improve precision because the two events are not independent "
            f"(BUSD wind-down preceded SVB by only 3 weeks)."
        )
    elif abs(r_pooled - r_svb) < 0.01 and n_pooled == n_svb:
        diagnosis = (
            f"Pooled r ({r_pooled:.4f}) is identical to SVB-only r ({r_svb:.4f}) AND n is unchanged "
            f"(n={n_pooled} vs n={n_svb}). This means the BUSD event contributed no additional "
            f"observations — likely because the BUSD baseline window is too short (only 7 days from "
            f"sample start) or entities had insufficient volume. The pooled row in Table E2 is "
            f"misleading and should either be corrected or removed."
        )
    else:
        diagnosis = (
            f"Pooled r ({r_pooled:.4f}) differs from SVB-only r ({r_svb:.4f}) by "
            f"{abs(r_pooled - r_svb):.4f}. The BUSD event contributes genuinely different "
            f"information (BUSD r = {r_busd:.4f}). The pooled value is correctly computed."
        )

    print(f"\n  DIAGNOSIS: {diagnosis}")

    result = {
        "svb_only": {
            "entities": svb_df["entity"].tolist(),
            "clii_scores": svb_df["clii"].tolist(),
            "retention_ratios": [round(x, 4) for x in svb_df["retention"].tolist()],
            "r": round(float(r_svb), 4),
            "p": round(float(p_svb), 4),
            "n": n_svb,
            "baseline_window": "2023-02-09 to 2023-03-08 (28 days)",
            "stress_window": "2023-03-09 to 2023-03-15 (7 days)",
        },
        "busd_only": {
            "entities": busd_df["entity"].tolist(),
            "clii_scores": busd_df["clii"].tolist(),
            "retention_ratios": [round(x, 4) for x in busd_df["retention"].tolist()],
            "r": round(float(r_busd), 4),
            "p": round(float(p_busd), 4),
            "n": n_busd,
            "baseline_window": "2023-02-06 to 2023-02-12 (7 days)",
            "stress_window": "2023-02-13 to 2023-02-19 (7 days)",
        },
        "pooled": {
            "r": round(float(r_pooled), 4),
            "p": round(float(p_pooled), 4),
            "n": n_pooled,
            "method": "Stacked observations (each entity appears once per event)",
        },
        "diagnosis": diagnosis,
        "paper_table_E2_comparison": {
            "reported_svb_r": -0.55,
            "reported_pooled_r": -0.55,
            "computed_svb_r": round(float(r_svb), 4),
            "computed_pooled_r": round(float(r_pooled), 4),
        },
    }

    save_json(result, "flow_retention_verification.json")
    return result


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("PHASE 1: NET-OF-INTERNAL COMPUTATIONS FOR PAPER v18")
    print("=" * 70)

    # Task 1
    hhi_result, hhi_df = task1_net_hhi()

    # Task 2
    corr_result = task2_tier_correlations()

    # Task 3
    retention_result = task3_flow_retention()

    # ── Consolidated Summary ──
    print("\n\n" + "=" * 70)
    print("=== PHASE 1 RESULTS SUMMARY ===")
    print("=" * 70)

    h = hhi_result
    print(f"\nTASK 1: Net HHI")
    print(f"  Entity HHI:  gross mean = {h['entity_hhi']['gross']['mean']:.0f}  →  net mean = {h['entity_hhi']['net']['mean']:.0f}  (Δ = {h['entity_hhi']['delta_mean']:+.0f})")
    print(f"  Above DOJ:   gross {h['entity_hhi']['gross']['pct_above_2500']:.1f}%         →  net {h['entity_hhi']['net']['pct_above_2500']:.1f}%")
    print(f"  Tier HHI:    gross mean = {h['tier_hhi']['gross']['mean']:.0f}  →  net mean = {h['tier_hhi']['net']['mean']:.0f}  (Δ = {h['tier_hhi']['delta_mean']:+.0f})")
    ts = h["tier_shares"]
    print(f"  Tier shares: gross T1/T2/T3 = {ts['gross']['T1']}/{ts['gross']['T2']}/{ts['gross']['T3']}  →  net = {ts['net']['T1']}/{ts['net']['T2']}/{ts['net']['T3']}")
    print(f"  PAPER IMPACT: {'NET BELOW 2500 — NEEDS REVISION' if h['net_below_2500'] else 'Net still above 2500 — claim holds'}")

    c = corr_result
    print(f"\nTASK 2: Net Tier Correlations (weekly)")
    for tier in ["T1", "T2", "T3"]:
        g = c["weekly_gross"][tier]
        n = c["weekly_net"][tier]
        d = c["delta"][f"{tier}_r"]
        print(f"  {tier}:  gross r = {g['r']:+.4f}  →  net r = {n['r']:+.4f}  (Δ = {d:+.4f})")
    t2_changed = abs(c["delta"]["T2_r"]) > 0.05
    print(f"  PAPER IMPACT: {'T2 changes materially — narrative review needed' if t2_changed else 'T2 essentially unchanged — narrative holds'}")

    r = retention_result
    print(f"\nTASK 3: Flow Retention Correlation")
    print(f"  SVB-only:  r = {r['svb_only']['r']:+.4f}, p = {r['svb_only']['p']:.4f}, n = {r['svb_only']['n']}")
    print(f"  BUSD-only: r = {r['busd_only']['r']:+.4f}, p = {r['busd_only']['p']:.4f}, n = {r['busd_only']['n']}")
    print(f"  Pooled:    r = {r['pooled']['r']:+.4f}, p = {r['pooled']['p']:.4f}, n = {r['pooled']['n']}")
    print(f"  PAPER IMPACT: {r['diagnosis'][:120]}...")

    print("\n" + "=" * 70)

    # Save consolidated summary
    summary = {
        "task1_net_hhi": {
            "entity_hhi_gross_mean": h["entity_hhi"]["gross"]["mean"],
            "entity_hhi_net_mean": h["entity_hhi"]["net"]["mean"],
            "entity_hhi_delta": h["entity_hhi"]["delta_mean"],
            "tier_shares_gross": ts["gross"],
            "tier_shares_net": ts["net"],
            "net_below_2500": h["net_below_2500"],
            "paper_impact": h["paper_impact"],
        },
        "task2_tier_correlations": {
            "T1_gross_r": c["weekly_gross"]["T1"]["r"],
            "T1_net_r": c["weekly_net"]["T1"]["r"],
            "T2_gross_r": c["weekly_gross"]["T2"]["r"],
            "T2_net_r": c["weekly_net"]["T2"]["r"],
            "T3_gross_r": c["weekly_gross"]["T3"]["r"],
            "T3_net_r": c["weekly_net"]["T3"]["r"],
            "T2_changed_materially": t2_changed,
            "paper_impact": c["paper_impact_T2"],
        },
        "task3_flow_retention": {
            "svb_r": r["svb_only"]["r"],
            "busd_r": r["busd_only"]["r"],
            "pooled_r": r["pooled"]["r"],
            "diagnosis": r["diagnosis"],
        },
    }
    save_json(summary, "phase1_summary.json")


if __name__ == "__main__":
    main()
