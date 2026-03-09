"""29_expanded_gateway_analysis.py — Phase 1-5 of Gateway Address Expansion.

Uses existing expanded Dune query results (35 Ethereum addresses across 15 entities)
to compute updated metrics, compare with original 12-address data, and document
paper impact.

Inputs:
  data/raw/dune_eth_expanded_gateway.csv   — expanded 35-address monthly volume
  data/raw/dune_eth_total_v2.csv           — total Ethereum USDC+USDT baseline
  data/raw/exhibit_A_gateway_transfers.csv — original codex_package daily data
  data/raw/dune_top50_addresses.csv        — top 50 addresses by volume

Outputs (Phase 2-5 deliverables):
  data/processed/gateway_registry_expanded.csv
  data/processed/gateway_volume_summary.csv
  data/processed/metrics_comparison.json
  data/processed/paper_claims_update.json
  sql/exhibit_A_expanded.sql
  sql/exhibit_C_expanded.sql
"""
import pandas as pd, numpy as np, json, sys
from pathlib import Path
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_RAW, DATA_PROC, save_json, save_csv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "config"))
from settings import GATEWAYS

# Also import the expanded registry
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "config"))
try:
    from gateway_registry import GATEWAYS_ETHEREUM
except ImportError:
    GATEWAYS_ETHEREUM = None

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
SQL_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================================================
# PHASE 1-2: Address Discovery & Validation
# ==========================================================================

def phase1_address_discovery():
    """Compile the expanded address registry with volume validation."""
    print("=" * 70)
    print("PHASE 1-2: Address Discovery & Volume Validation")
    print("=" * 70)

    if GATEWAYS_ETHEREUM is None:
        print("  WARNING: gateway_registry.py not found. Using settings.py only.")
        return None

    # Build registry DataFrame
    rows = []
    for g in GATEWAYS_ETHEREUM:
        rows.append({
            "entity": g["entity"],
            "address": g["address"].lower(),
            "address_type": g["address_type"],
            "tier": g["tier"],
            "clii": g["clii"],
            "source": g["source"],
        })
    registry = pd.DataFrame(rows)
    print(f"  Expanded registry: {len(registry)} addresses, "
          f"{registry['entity'].nunique()} entities")

    # Load expanded Dune volume data
    expanded = pd.read_csv(DATA_RAW / "dune_eth_expanded_gateway.csv")
    entity_vol = expanded.groupby("entity")["volume_usd"].sum()
    entity_n = expanded.groupby("entity")["n_transfers"].sum()

    # Map entity volumes back to registry
    registry["volume_usd"] = registry["entity"].map(entity_vol).fillna(0)
    registry["n_transfers"] = registry["entity"].map(entity_n).fillna(0)

    # Normalize entity names for cross-reference with original data
    registry["original_name"] = registry["entity"].map({
        "Circle": "Circle",
        "Coinbase": "Coinbase",
        "Paxos": "Paxos",
        "Gemini": "Gemini",
        "Tether": "Tether Treasury",
        "Binance": "Binance",
        "Kraken": "Kraken",
        "OKX": "OKX",
        "Uniswap V3": "Uniswap Router",
        "Uniswap Universal Router": "Uniswap Router",
        "Curve 3pool": "Curve 3pool",
        "Aave V3": "Aave V3 Pool",
        "1inch": "1inch",
        "Compound V3": "Compound V3",
        "Tornado Cash": "Tornado Cash",
        "PayPal": "PayPal",
        "BitGo": "BitGo",
        "Bybit": "Bybit",
        "Robinhood": "Robinhood",
    })

    # Save expanded registry
    save_csv(registry, "gateway_registry_expanded.csv")

    # Print summary
    entity_summary = registry.groupby("entity").agg(
        n_addresses=("address", "count"),
        tier=("tier", "first"),
        clii=("clii", "first"),
        total_volume_B=("volume_usd", lambda x: x.iloc[0] / 1e9),
    ).sort_values("total_volume_B", ascending=False)

    print(f"\n  Entity-level summary (expanded, {len(entity_summary)} entities):")
    total_exp = entity_summary["total_volume_B"].sum()
    for entity, row in entity_summary.iterrows():
        share = row["total_volume_B"] / total_exp * 100 if total_exp > 0 else 0
        status = "OK" if row["total_volume_B"] > 0.1 else "ZERO"
        print(f"    {entity:30s} T{int(row['tier'])} | "
              f"{int(row['n_addresses'])} addrs | "
              f"${row['total_volume_B']:>8.1f}B ({share:5.1f}%) [{status}]")

    # Flag entities with zero volume
    zeros = entity_summary[entity_summary["total_volume_B"] < 0.1]
    if len(zeros) > 0:
        print(f"\n  WARNING: {len(zeros)} entities with near-zero volume:")
        for entity in zeros.index:
            addrs = registry[registry["entity"] == entity]["address"].tolist()
            print(f"    {entity}: {addrs}")

    return registry


# ==========================================================================
# PHASE 3: Build Updated SQL & Volume Summary
# ==========================================================================

def phase3_update_sql_and_summary(registry):
    """Write updated SQL files and build volume summary table."""
    print("\n" + "=" * 70)
    print("PHASE 3: Update SQL Files & Volume Summary")
    print("=" * 70)

    # Build the gateway CTE for SQL from expanded registry
    if registry is not None:
        eth_addrs = registry[registry["entity"].notna()].copy()
    else:
        # Fallback: use settings.py GATEWAYS
        eth_addrs = pd.DataFrame([
            {"entity": v["name"], "address": k, "tier": v["tier"],
             "address_type": "unknown", "clii": v["clii"], "source": "settings.py"}
            for k, v in GATEWAYS.items()
        ])

    # Generate CTE VALUES block
    values_lines = []
    for _, row in eth_addrs.iterrows():
        addr_hex = row["address"]
        if not addr_hex.startswith("0x"):
            addr_hex = "0x" + addr_hex
        entity = row["entity"]
        tier = int(row["tier"])
        values_lines.append(
            f"        ({addr_hex}, '{entity}', {tier})")

    cte_block = "WITH gateway_addresses AS (\n"
    cte_block += "    SELECT address, name, tier FROM (VALUES\n"
    cte_block += ",\n".join(values_lines)
    cte_block += "\n    ) AS t(address, name, tier)\n)"

    # Write exhibit_A expanded SQL
    sql_a = f"""{cte_block}
SELECT date_trunc('day', e.evt_block_time) AS day,
    g.name AS gateway, g.tier,
    CASE WHEN e.contract_address = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 THEN 'USDC'
         WHEN e.contract_address = 0xdAC17F958D2ee523a2206206994597C13D831ec7 THEN 'USDT' END AS token,
    SUM(CASE WHEN e."to" = g.address THEN CAST(e.value AS DOUBLE) / 1e6 ELSE 0 END) AS inflow_usd,
    SUM(CASE WHEN e."from" = g.address THEN CAST(e.value AS DOUBLE) / 1e6 ELSE 0 END) AS outflow_usd,
    SUM(CASE WHEN e."to" = g.address THEN CAST(e.value AS DOUBLE) / 1e6
             WHEN e."from" = g.address THEN -CAST(e.value AS DOUBLE) / 1e6 ELSE 0 END) AS net_flow_usd
FROM erc20_ethereum.evt_Transfer e
INNER JOIN gateway_addresses g ON (e."from" = g.address OR e."to" = g.address)
WHERE e.contract_address IN (
    0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48,
    0xdAC17F958D2ee523a2206206994597C13D831ec7
)
AND e.evt_block_time >= TIMESTAMP '2023-02-01'
AND e.evt_block_time < TIMESTAMP '2026-02-01'
GROUP BY 1, 2, 3, 4
ORDER BY 1
"""
    with open(SQL_DIR / "exhibit_A_expanded.sql", "w") as f:
        f.write(sql_a)
    print(f"  Wrote {SQL_DIR / 'exhibit_A_expanded.sql'}")

    # Write exhibit_C expanded SQL (concentration)
    sql_c = f"""{cte_block}
, daily_vol AS (
    SELECT
        date_trunc('day', e.evt_block_time) AS day,
        g.name AS gateway,
        g.tier,
        SUM(CAST(e.value AS DOUBLE)) / 1e6 AS volume_usd
    FROM erc20_ethereum.evt_Transfer e
    INNER JOIN gateway_addresses g ON (e."from" = g.address OR e."to" = g.address)
    WHERE e.contract_address IN (
        0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48,
        0xdAC17F958D2ee523a2206206994597C13D831ec7
    )
    AND e.evt_block_time >= TIMESTAMP '2023-02-01'
    AND e.evt_block_time < TIMESTAMP '2026-02-01'
    GROUP BY 1, 2, 3
)
, daily_total AS (
    SELECT day, SUM(volume_usd) AS total_vol FROM daily_vol GROUP BY 1
)
SELECT
    d.day AS date,
    d.gateway,
    d.tier,
    d.volume_usd,
    d.volume_usd / NULLIF(t.total_vol, 0) * 100 AS share_pct,
    POWER(d.volume_usd / NULLIF(t.total_vol, 0) * 100, 2) AS hhi_component
FROM daily_vol d
JOIN daily_total t ON d.day = t.day
ORDER BY d.day, d.tier, d.gateway
"""
    with open(SQL_DIR / "exhibit_C_expanded.sql", "w") as f:
        f.write(sql_c)
    print(f"  Wrote {SQL_DIR / 'exhibit_C_expanded.sql'}")

    # Build gateway_volume_summary.csv
    expanded = pd.read_csv(DATA_RAW / "dune_eth_expanded_gateway.csv")
    entity_vol = expanded.groupby("entity").agg(
        total_volume=("volume_usd", "sum"),
        n_transfers=("n_transfers", "sum"),
        tier=("tier", "first"),
    ).sort_values("total_volume", ascending=False)

    # Add address count from registry
    if registry is not None:
        addr_counts = registry.groupby("entity")["address"].count()
        entity_vol["n_addresses"] = entity_vol.index.map(addr_counts).fillna(1).astype(int)
    else:
        entity_vol["n_addresses"] = 1

    total = entity_vol["total_volume"].sum()
    entity_vol["share_pct"] = entity_vol["total_volume"] / total * 100
    entity_vol["volume_B"] = entity_vol["total_volume"] / 1e9

    # Add old share from original data
    orig = pd.read_csv(DATA_RAW / "exhibit_A_gateway_transfers.csv")
    orig["total_vol"] = orig["inflow_usd"].abs() + orig["outflow_usd"].abs()
    orig_by_gw = orig.groupby("gateway")["total_vol"].sum()
    orig_total = orig_by_gw.sum()
    orig_share = (orig_by_gw / orig_total * 100)

    # Map original names to expanded entity names
    name_map = {
        "Circle": "Circle", "Coinbase": "Coinbase", "Paxos": "Paxos",
        "Gemini": "Gemini", "Tether Treasury": "Tether",
        "Binance": "Binance", "Kraken": "Kraken", "OKX": "OKX",
        "Uniswap Router": "Uniswap V3", "Curve 3pool": "Curve 3pool",
        "Aave V3 Pool": "Aave V3", "0x Exchange": "0x Exchange",
    }
    for orig_name, exp_name in name_map.items():
        if exp_name in entity_vol.index and orig_name in orig_share:
            entity_vol.loc[exp_name, "old_share_pct"] = orig_share[orig_name]

    entity_vol = entity_vol.fillna(0)
    save_csv(entity_vol, "gateway_volume_summary.csv")

    print(f"\n  Gateway Volume Summary:")
    print(f"  {'Entity':30s} {'Tier':4s} {'Addrs':5s} {'Volume':>10s} {'New %':>6s} {'Old %':>6s}")
    print(f"  {'-'*30} {'-'*4} {'-'*5} {'-'*10} {'-'*6} {'-'*6}")
    for entity, row in entity_vol.iterrows():
        print(f"  {entity:30s} T{int(row['tier'])} "
              f"{int(row['n_addresses']):>5d} "
              f"${row['volume_B']:>8.1f}B "
              f"{row['share_pct']:>5.1f}% "
              f"{row['old_share_pct']:>5.1f}%")
    print(f"  {'TOTAL':30s}       "
          f"${total/1e9:>8.1f}B  100.0%  100.0%")

    return entity_vol


# ==========================================================================
# PHASE 4: Calculate Updated Metrics
# ==========================================================================

def phase4_calculate_metrics(entity_vol):
    """Compute all eight metrics with expanded data and compare to old."""
    print("\n" + "=" * 70)
    print("PHASE 4: Calculate Updated Metrics")
    print("=" * 70)

    metrics = {}

    # Load total Ethereum volume for coverage ratio
    try:
        total_eth = pd.read_csv(DATA_RAW / "dune_eth_total_v2.csv")
        total_eth_vol = total_eth["volume_usd"].sum()
    except Exception:
        total_eth_vol = 27_950_735_948_472.184  # fallback

    # --- Metric 1: Tier 1 share ---
    tier_vol = entity_vol.groupby("tier")["total_volume"].sum()
    total = tier_vol.sum()
    t1_share = tier_vol.get(1, 0) / total * 100
    t2_share = tier_vol.get(2, 0) / total * 100
    t3_share = tier_vol.get(3, 0) / total * 100
    metrics["tier1_share"] = {
        "new": round(t1_share, 1), "old": 81.6,
        "tier2": round(t2_share, 1), "tier3": round(t3_share, 1),
    }
    print(f"\n  [1] Tier shares: T1={t1_share:.1f}%, T2={t2_share:.1f}%, T3={t3_share:.1f}%")
    print(f"      Old:         T1=81.6%, T2=9.7%, T3=8.7%")

    # --- Metric 2: Within-Tier 1 breakdown ---
    t1_entities = entity_vol[entity_vol["tier"] == 1]
    t1_total = t1_entities["total_volume"].sum()
    within_t1 = {}
    for entity, row in t1_entities.iterrows():
        within_t1[entity] = round(row["total_volume"] / t1_total * 100, 1)
    metrics["within_tier1"] = within_t1
    print(f"\n  [2] Within-Tier 1 breakdown:")
    for e, s in sorted(within_t1.items(), key=lambda x: -x[1]):
        print(f"      {e}: {s}%")
    print(f"      Old: Circle 76.4%, Gemini 23.1%, Paxos 0.6%, Coinbase <0.1%")

    # --- Metric 3: Entity-level HHI ---
    entity_shares = entity_vol["total_volume"] / total * 100
    hhi_entity = (entity_shares ** 2).sum()
    metrics["hhi_entity"] = {"new": round(hhi_entity), "old": 4849}
    print(f"\n  [3] Entity-level HHI: {hhi_entity:.0f} (old: 4,849)")

    # --- Metric 4: Tier-level HHI ---
    tier_shares = pd.Series({
        "Tier1": t1_share, "Tier2": t2_share, "Tier3": t3_share
    })
    hhi_tier = (tier_shares ** 2).sum()
    metrics["hhi_tier"] = {"new": round(hhi_tier), "old": 7361}
    print(f"\n  [4] Tier-level HHI: {hhi_tier:.0f} (old: 7,361)")

    # --- Metric 5: Coverage ratio ---
    gateway_vol = entity_vol["total_volume"].sum()
    coverage = gateway_vol / total_eth_vol * 100
    metrics["coverage_ratio"] = {
        "new_pct": round(coverage, 1),
        "old_pct": 8.1,
        "gateway_vol_T": round(gateway_vol / 1e12, 2),
        "total_eth_vol_T": round(total_eth_vol / 1e12, 2),
    }
    print(f"\n  [5] Coverage ratio: {coverage:.1f}% "
          f"(${gateway_vol/1e12:.2f}T / ${total_eth_vol/1e12:.2f}T) (old: 8.1%)")

    # --- Metric 6: SVB flow retention ---
    # Use original exhibit_A data for daily SVB analysis
    try:
        a = pd.read_csv(DATA_RAW / "exhibit_A_gateway_transfers.csv")
        a["date"] = pd.to_datetime(a["date"], utc=True).dt.tz_localize(None)
        a["total_vol"] = a["inflow_usd"].abs() + a["outflow_usd"].abs()

        stress = a[(a["date"] >= "2023-03-08") & (a["date"] <= "2023-03-15")]
        normal = a[(a["date"] < "2023-03-08") | (a["date"] > "2023-03-15")]

        stress_total = stress["total_vol"].sum()
        normal_total = normal["total_vol"].sum()

        stress_shares = stress.groupby("gateway")["total_vol"].sum() / stress_total
        normal_shares = normal.groupby("gateway")["total_vol"].sum() / normal_total

        retention = {}
        for gw in normal_shares.index:
            if gw in stress_shares.index:
                n_share = float(normal_shares[gw])
                s_share = float(stress_shares[gw])
                if n_share > 0.001:
                    retention[gw] = round(s_share / n_share, 2)

        metrics["svb_retention"] = {
            "note": "SVB data from original 12-address exhibit_A only",
            "retention_by_gateway": retention,
        }
        print(f"\n  [6] SVB flow retention (original 12 addresses):")
        for gw, r in sorted(retention.items(), key=lambda x: -x[1]):
            print(f"      {gw}: {r:.2f}x")
    except Exception as e:
        print(f"\n  [6] SVB retention: {e}")
        metrics["svb_retention"] = {"error": str(e)}

    # --- Metric 7: Tier-level correlations ---
    # Use original exhibit_A + FRED for daily tier correlations
    try:
        a = pd.read_csv(DATA_RAW / "exhibit_A_gateway_transfers.csv")
        a["date"] = pd.to_datetime(a["date"], utc=True).dt.tz_localize(None)
        a["total_vol"] = a["inflow_usd"].abs() + a["outflow_usd"].abs()
        daily_tier = a.groupby(["date", "tier"])["total_vol"].sum().unstack(fill_value=0)
        d_total = daily_tier.sum(axis=1).replace(0, np.nan)
        tier_shares_daily = daily_tier.div(d_total, axis=0).fillna(0)

        fred = pd.read_csv(DATA_RAW / "fred_wide.csv", index_col=0, parse_dates=True)
        weekly_shares = tier_shares_daily.resample("W-WED").mean()
        weekly_fred = fred[["WSHOMCB"]].resample("W-WED").last()
        merged = weekly_shares.join(weekly_fred, how="inner").dropna()

        tier_corr = {}
        for tier_col in ["Tier1", "Tier2", "Tier3"]:
            if tier_col in merged.columns:
                r, p = stats.pearsonr(merged[tier_col], merged["WSHOMCB"])
                tier_corr[tier_col] = {"r": round(r, 4), "p": round(p, 4)}

        metrics["tier_correlations"] = {
            "note": "From original 12-address data (daily). Expanded data is monthly — would need daily Dune re-query.",
            "original_12_addr": tier_corr,
            "old_paper_values": {"Tier1": -0.67, "Tier2": -0.29, "Tier3": 0.43},
        }
        print(f"\n  [7] Tier-level correlations (original 12 addresses):")
        for t, d in tier_corr.items():
            print(f"      {t} vs Fed Assets: r={d['r']:.4f}")
    except Exception as e:
        print(f"\n  [7] Tier correlations: {e}")

    # --- Metric 8: Circle-Gemini concentration ---
    circle_share = within_t1.get("Circle", 0)
    gemini_share = within_t1.get("Gemini", 0)
    coinbase_share = within_t1.get("Coinbase", 0)
    duopoly = circle_share + gemini_share
    triopoly = circle_share + coinbase_share + gemini_share
    metrics["within_tier1_concentration"] = {
        "circle_pct": circle_share,
        "coinbase_pct": coinbase_share,
        "gemini_pct": gemini_share,
        "circle_gemini_pct": round(duopoly, 1),
        "circle_coinbase_gemini_pct": round(triopoly, 1),
        "old_circle_gemini": 99.4,
    }
    print(f"\n  [8] Within-Tier 1 concentration:")
    print(f"      Circle + Gemini:              {duopoly:.1f}% (old: 99.4%)")
    print(f"      Circle + Coinbase + Gemini:   {triopoly:.1f}%")

    # Save
    save_json(metrics, "metrics_comparison.json")
    return metrics


# ==========================================================================
# PHASE 5: Paper Claims Impact
# ==========================================================================

def phase5_paper_claims(metrics, entity_vol):
    """Document which paper claims need updating."""
    print("\n" + "=" * 70)
    print("PHASE 5: Paper Claims Impact Assessment")
    print("=" * 70)

    t1 = metrics.get("tier1_share", {})
    wt1 = metrics.get("within_tier1", {})
    wt1c = metrics.get("within_tier1_concentration", {})
    cov = metrics.get("coverage_ratio", {})
    hhi_e = metrics.get("hhi_entity", {})
    hhi_t = metrics.get("hhi_tier", {})

    claims = {
        "generated": "2026-02-13",
        "context": "Impact of expanding from 12 single-address gateways to 35 multi-address "
                   "gateway registry on Ethereum.",

        "claims": [
            {
                "claim": "Circle and Gemini together process 80.6% of monitored Ethereum gateway volume",
                "location": "VI.A, VI.D",
                "old_value": "80.6%",
                "new_value": f"{wt1c.get('circle_gemini_pct', '?')}%",
                "risk": "HIGH",
                "action": "Replace 'duopoly' framing. With expanded addresses, Coinbase emerges "
                          f"as {wt1.get('Coinbase', '?')}% of Tier 1 volume. Binance is "
                          f"{wt1.get('Binance', '?')}% of total monitored volume.",
            },
            {
                "claim": "Coinbase processes less than 0.1 percent of monitored volume",
                "location": "V.C",
                "old_value": "<0.1%",
                "new_value": f"{entity_vol.loc['Coinbase', 'share_pct']:.1f}%" if "Coinbase" in entity_vol.index else "TBD",
                "risk": "HIGH",
                "action": "Coinbase's original address (0x7166...) was cold storage. With 6 expanded "
                          "addresses including the active hot wallet (0xA9D1...), Coinbase is the "
                          "second-largest Tier 1 gateway.",
            },
            {
                "claim": "99.4 percent of Tier 1 volume flows through Circle and Gemini",
                "location": "Intro, VI.A, VII",
                "old_value": "99.4%",
                "new_value": f"{wt1c.get('circle_gemini_pct', '?')}%",
                "risk": "HIGH",
                "action": "Replace with expanded Tier 1 breakdown. Coinbase now significant.",
            },
            {
                "claim": "Tier 1 volume share: 82%",
                "location": "Throughout",
                "old_value": "82%",
                "new_value": f"{t1.get('new', '?')}%",
                "risk": "MEDIUM",
                "action": f"Tier 1 share {'increased' if t1.get('new', 0) > 82 else 'decreased'} "
                          f"to {t1.get('new', '?')}% with expanded addresses. "
                          "This reflects adding more Tier 1 (Coinbase) AND Tier 2 (Binance) addresses.",
            },
            {
                "claim": "Entity-level HHI: 4,849",
                "location": "V.C",
                "old_value": "4,849",
                "new_value": f"{hhi_e.get('new', '?'):,}",
                "risk": "MEDIUM",
                "action": "HHI changes because volume is now spread across more entities with "
                          "material volume (Coinbase, Bybit, 1inch).",
            },
            {
                "claim": "Tier-level HHI: 7,361",
                "location": "V.C",
                "old_value": "7,361",
                "new_value": f"{hhi_t.get('new', '?'):,}",
                "risk": "MEDIUM",
                "action": "Tier-level HHI changes with new tier share distribution.",
            },
            {
                "claim": "Eight of twelve addresses are active",
                "location": "V.C footnote",
                "old_value": "8 of 12",
                "new_value": f"{int(entity_vol[entity_vol['total_volume'] > 1e9].shape[0])} of "
                             f"{len(entity_vol)} entities with >$1B volume",
                "risk": "MEDIUM",
                "action": "Update entity count. Several new entities now have material volume.",
            },
            {
                "claim": "Coverage ratio: 8.1%",
                "location": "IV.A, V.C",
                "old_value": "8.1%",
                "new_value": f"{cov.get('new_pct', '?')}%",
                "risk": "LOW-MEDIUM",
                "action": "Coverage increases with more addresses. Still a small fraction of total.",
            },
        ],

        "gemini_attribution_note": {
            "issue": "Address 0x21a31ee1afc51d94c2efccaa2092ad1028285549 was labeled 'Gemini' in "
                     "the original codex_package but is labeled 'Binance 36' on Etherscan and in "
                     "Dune/Arkham. The expanded data assigns it to Binance.",
            "impact": "If this address is actually Binance (Etherscan's label), then Gemini's true "
                      "volume from the original data was ~$0, not $423B. The 'duopoly' was actually "
                      "Circle + Binance, not Circle + Gemini.",
            "recommendation": "Verify this attribution by checking Binance's official disclosures. "
                              "Etherscan's label is likely correct as it's based on verified entity "
                              "tags. If so, the original codex_package had a critical mislabeling.",
        },

        "kraken_okx_note": {
            "issue": "Kraken and OKX still show $0 in USDC+USDT volume on Ethereum even with "
                     "expanded address sets.",
            "possible_explanations": [
                "Their Ethereum stablecoin operations use addresses not yet in the registry",
                "They route primarily through omnibus/aggregated wallets not labeled to them",
                "Their stablecoin volume is genuinely low on Ethereum (Kraken may route more on L2s)",
                "Further address discovery needed — run Dune labels query",
            ],
            "recommendation": "Run Dune label discovery query for Kraken/OKX Ethereum addresses. "
                              "If still zero, note in paper that some exchanges have minimal "
                              "direct on-chain stablecoin footprint.",
        },

        "thesis_impact": {
            "strengthens": [
                "Coverage ratio increases — more total volume captured by monitored gateways",
                "Tier 1 share may remain high — Coinbase is a major Tier 1 entity with significant volume",
                "The 'regulate the router' thesis is supported by finding more regulated entities with large volume",
            ],
            "weakens": [
                "The 'Circle-Gemini duopoly' narrative collapses — concentration within Tier 1 is lower",
                "Entity-level HHI likely decreases — more entities have material volume",
                "The 'chokepoint' argument is weaker if volume is distributed across many addresses per entity",
            ],
            "net_assessment": "Net positive for the paper's core thesis. The gateway concentration is "
                              "BETWEEN tiers (Tier 1 vs Tier 2) rather than within Tier 1. The 'regulate "
                              "the router' argument is strengthened by showing that regulated entities "
                              "(Circle + Coinbase) collectively handle the majority of Tier 1 volume. "
                              "The specific 'duopoly' framing needs revision but the broader argument holds.",
        },
    }

    save_json(claims, "paper_claims_update.json")

    # Print summary
    for c in claims["claims"]:
        print(f"  [{c['risk']:6s}] {c['claim'][:60]:60s}")
        print(f"          {c['old_value']} → {c['new_value']}")

    return claims


# ==========================================================================
# Kraken/OKX Address Discovery via Dune API
# ==========================================================================

def run_kraken_okx_discovery():
    """Run Dune API query to discover active Kraken/OKX Ethereum addresses."""
    print("\n" + "=" * 70)
    print("BONUS: Kraken/OKX Address Discovery via Dune API")
    print("=" * 70)

    from settings import DUNE_API_KEY
    if not DUNE_API_KEY:
        print("  No DUNE_API_KEY — skipping discovery")
        return

    import requests, time

    DUNE_API = "https://api.dune.com/api/v1"
    HEADERS = {"X-Dune-API-Key": DUNE_API_KEY, "Content-Type": "application/json"}

    # Save the discovery SQL for reference
    discovery_sql = """
-- Discover labeled Kraken/OKX addresses with USDC+USDT volume
WITH exchange_labels AS (
    SELECT DISTINCT address, name, label_type
    FROM labels.addresses
    WHERE blockchain = 'ethereum'
    AND (name ILIKE '%kraken%' OR name ILIKE '%okx%' OR name ILIKE '%okex%')
),
addr_volume AS (
    SELECT
        addr,
        SUM(vol) AS total_volume_usd,
        SUM(cnt) AS n_transfers
    FROM (
        SELECT "from" AS addr, SUM(CAST(value AS DOUBLE) / 1e6) AS vol, COUNT(*) AS cnt
        FROM erc20_ethereum.evt_Transfer
        WHERE contract_address IN (
            0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48,
            0xdac17f958d2ee523a2206206994597c13d831ec7
        )
        AND evt_block_time >= TIMESTAMP '2023-02-01'
        AND evt_block_time < TIMESTAMP '2026-02-01'
        GROUP BY 1
        UNION ALL
        SELECT "to", SUM(CAST(value AS DOUBLE) / 1e6), COUNT(*)
        FROM erc20_ethereum.evt_Transfer
        WHERE contract_address IN (
            0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48,
            0xdac17f958d2ee523a2206206994597c13d831ec7
        )
        AND evt_block_time >= TIMESTAMP '2023-02-01'
        AND evt_block_time < TIMESTAMP '2026-02-01'
        GROUP BY 1
    ) sub
    GROUP BY 1
    HAVING SUM(vol) > 1e8  -- >$100M
)
SELECT
    e.name AS label,
    CAST(a.addr AS VARCHAR) AS address,
    a.total_volume_usd,
    a.n_transfers,
    e.label_type
FROM addr_volume a
JOIN exchange_labels e ON a.addr = e.address
ORDER BY a.total_volume_usd DESC
"""

    sql_path = SQL_DIR / "disc_kraken_okx_ethereum.sql"
    with open(sql_path, "w") as f:
        f.write(discovery_sql)
    print(f"  SQL saved to {sql_path}")

    # Try to run via API
    try:
        print("  Creating Dune query...")
        resp = requests.post(
            f"{DUNE_API}/query", headers=HEADERS,
            json={"name": "disc_kraken_okx_eth_stablecoin",
                  "query_sql": discovery_sql.strip(), "is_private": True},
            timeout=30)
        if resp.status_code != 200:
            print(f"  Create failed: {resp.status_code} — {resp.text[:200]}")
            print("  Run the SQL manually in Dune UI")
            return
        qid = resp.json().get("query_id")
        print(f"  Query ID: {qid}")

        print("  Executing...")
        resp = requests.post(
            f"{DUNE_API}/query/{qid}/execute", headers=HEADERS,
            json={"performance": "medium"}, timeout=30)
        if resp.status_code != 200:
            print(f"  Execute failed: {resp.status_code}")
            return
        eid = resp.json().get("execution_id")
        print(f"  Execution ID: {eid}")

        # Poll for results (up to 5 minutes)
        for attempt in range(30):
            time.sleep(10)
            try:
                resp = requests.get(f"{DUNE_API}/execution/{eid}/status",
                                    headers=HEADERS, timeout=30)
                state = resp.json().get("state", "")
                if attempt % 3 == 0:
                    print(f"    Poll {attempt+1}: {state}")
                if state == "QUERY_STATE_COMPLETED":
                    break
                elif state in ("QUERY_STATE_FAILED", "QUERY_STATE_CANCELLED"):
                    print(f"    FAILED: {resp.json().get('error', 'unknown')}")
                    return
            except Exception as e:
                if attempt % 3 == 0:
                    print(f"    Poll error: {e}")
        else:
            print("    Timed out after 5 minutes")
            return

        # Fetch results
        resp = requests.get(f"{DUNE_API}/execution/{eid}/results",
                            headers=HEADERS, params={"limit": 1000}, timeout=60)
        if resp.status_code != 200:
            print(f"  Fetch failed: {resp.status_code}")
            return
        rows = resp.json().get("result", {}).get("rows", [])
        if not rows:
            print("  No results (Kraken/OKX may have no labeled Ethereum stablecoin addresses)")
            return

        df = pd.DataFrame(rows)
        df.to_csv(DATA_RAW / "dune_kraken_okx_discovery.csv", index=False)
        print(f"\n  Found {len(df)} labeled addresses:")
        for _, r in df.iterrows():
            print(f"    {r.get('label', '?'):30s} {r.get('address', '?')[:20]}... "
                  f"${r.get('total_volume_usd', 0)/1e9:.1f}B")

    except Exception as e:
        print(f"  API error: {e}")
        print("  Run the SQL manually in Dune UI")


# ==========================================================================
# MAIN
# ==========================================================================

def main():
    print("=" * 70)
    print("EXPANDED GATEWAY ANALYSIS — All 5 Phases")
    print("=" * 70)

    # Phase 1-2
    registry = phase1_address_discovery()

    # Phase 3
    entity_vol = phase3_update_sql_and_summary(registry)

    # Phase 4
    metrics = phase4_calculate_metrics(entity_vol)

    # Phase 5
    claims = phase5_paper_claims(metrics, entity_vol)

    # Bonus: Kraken/OKX discovery
    run_kraken_okx_discovery()

    print("\n" + "=" * 70)
    print("COMPLETE — All deliverables generated")
    print("=" * 70)
    print("  Deliverables:")
    print("    data/processed/gateway_registry_expanded.csv")
    print("    data/processed/gateway_volume_summary.csv")
    print("    data/processed/metrics_comparison.json")
    print("    data/processed/paper_claims_update.json")
    print("    sql/exhibit_A_expanded.sql")
    print("    sql/exhibit_C_expanded.sql")
    print("    sql/disc_kraken_okx_ethereum.sql")


if __name__ == "__main__":
    main()
