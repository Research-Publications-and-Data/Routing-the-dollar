"""Task 11: Use-case decomposition from Artemis API data.

Pulls stablecoin transfer volume by chain and category from Artemis,
computes use-case shares (CEX trading, DeFi, P2P, bridge, payments, other).

Artemis has two classification systems:
  - Application categories (defi, cex, bridge, payments): available for ETH, SOL, BASE
  - P2P transfers: available for all chains (separate endpoint, different taxonomy)

Output: data/processed/usecase_decomposition.csv, data/processed/usecase_decomposition_results.json
"""
import requests, pandas as pd, numpy as np, time, sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "config"))
from settings import PRIMARY_START, PRIMARY_END, ARTEMIS_API_KEY
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_PROC, save_csv, save_json

BASE_URL = "https://data-svc.artemisxyz.com/data/api"
CHAINS = ["eth", "sol", "tron", "bsc", "base", "arbitrum", "polygon", "avalanche", "optimism"]
CATEGORY_CHAINS = ["eth", "sol", "base"]
CATEGORIES = ["defi", "cex", "bridge", "payments"]


def fetch_metric(symbols, metric, start, end, granularity="MONTH"):
    """Fetch a metric from Artemis API. Returns dict of {symbol: {metric: [{date, val}]}}."""
    url = (f"{BASE_URL}/{metric}?symbols={symbols}"
           f"&startDate={start}&endDate={end}&granularity={granularity}"
           f"&APIKey={ARTEMIS_API_KEY}")
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 429:
            print("    Rate limited, waiting 5s...")
            time.sleep(5)
            return fetch_metric(symbols, metric, start, end, granularity)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict):
                syms = data.get("data", {})
                if isinstance(syms, dict):
                    syms = syms.get("symbols", syms)
                    if isinstance(syms, dict):
                        return syms
        else:
            print(f"    HTTP {resp.status_code} for {metric}/{symbols}")
    except Exception as e:
        print(f"    Error: {e}")
    return {}


def extract_series(api_result, symbol, metric):
    """Extract a time series from API result into a pandas Series."""
    sym_data = api_result.get(symbol, {})
    if not isinstance(sym_data, dict):
        return pd.Series(dtype=float)
    vals = sym_data.get(metric, [])
    if not isinstance(vals, list) or len(vals) == 0:
        return pd.Series(dtype=float)
    return pd.Series(
        {pd.Timestamp(v["date"]): v["val"] for v in vals if "val" in v and "date" in v},
        dtype=float
    )


def main():
    if not ARTEMIS_API_KEY:
        print("ERROR: Set ARTEMIS_API_KEY in config/settings.py")
        sys.exit(1)

    print("=" * 60)
    print("USE-CASE DECOMPOSITION (Artemis API)")
    print("=" * 60)

    start, end = PRIMARY_START, PRIMARY_END

    # 1. Total adjusted volume by chain (monthly)
    print("\n--- Total adjusted stablecoin transfer volume by chain ---")
    chain_str = ",".join(CHAINS)
    total_result = fetch_metric(chain_str, "ARTEMIS_STABLECOIN_TRANSFER_VOLUME", start, end)
    time.sleep(0.5)

    chain_totals = {}
    for chain in CHAINS:
        s = extract_series(total_result, chain, "ARTEMIS_STABLECOIN_TRANSFER_VOLUME")
        if len(s) > 0:
            chain_totals[chain] = s
            print(f"  {chain}: {len(s)} months, total ${s.sum()/1e12:.2f}T")

    # 2. P2P volume by chain (monthly)
    print("\n--- P2P stablecoin transfer volume by chain ---")
    p2p_result = fetch_metric(chain_str, "P2P_STABLECOIN_TRANSFER_VOLUME", start, end)
    time.sleep(0.5)

    chain_p2p = {}
    for chain in CHAINS:
        s = extract_series(p2p_result, chain, "P2P_STABLECOIN_TRANSFER_VOLUME")
        if len(s) > 0:
            chain_p2p[chain] = s
            print(f"  {chain}: {len(s)} months, total ${s.sum()/1e12:.2f}T")

    # 3. Category breakdown for chains that support it
    print("\n--- Category breakdown (ETH, SOL, BASE) ---")
    category_data = {}
    for cat in CATEGORIES:
        category_data[cat] = {}
        cat_symbols = ",".join([f"{cat}-{ch}" for ch in CATEGORY_CHAINS])
        cat_result = fetch_metric(cat_symbols, "ARTEMIS_STABLECOIN_TRANSFER_VOLUME", start, end)
        time.sleep(0.5)
        for chain in CATEGORY_CHAINS:
            sym = f"{cat}-{chain}"
            s = extract_series(cat_result, sym, "ARTEMIS_STABLECOIN_TRANSFER_VOLUME")
            if len(s) > 0:
                category_data[cat][chain] = s
                print(f"  {sym}: {len(s)} months, total ${s.sum()/1e12:.3f}T")

    # 4. Build monthly DataFrame
    print("\n--- Building monthly decomposition ---")

    all_months = set()
    for s in chain_totals.values():
        all_months.update(s.index)
    months = sorted(all_months)

    rows = []
    for m in months:
        # All-chain totals
        total_all = sum(s.get(m, 0) for s in chain_totals.values())
        p2p_all = sum(s.get(m, 0) for s in chain_p2p.values())

        # Category-chain totals (ETH+SOL+BASE only)
        total_cat_chains = sum(chain_totals.get(ch, pd.Series(dtype=float)).get(m, 0) for ch in CATEGORY_CHAINS)
        defi = sum(category_data.get("defi", {}).get(ch, pd.Series(dtype=float)).get(m, 0) for ch in CATEGORY_CHAINS)
        cex = sum(category_data.get("cex", {}).get(ch, pd.Series(dtype=float)).get(m, 0) for ch in CATEGORY_CHAINS)
        bridge = sum(category_data.get("bridge", {}).get(ch, pd.Series(dtype=float)).get(m, 0) for ch in CATEGORY_CHAINS)
        payments = sum(category_data.get("payments", {}).get(ch, pd.Series(dtype=float)).get(m, 0) for ch in CATEGORY_CHAINS)
        cat_sum = defi + cex + bridge + payments
        other_cat = max(0, total_cat_chains - cat_sum)

        rows.append({
            "date": m,
            "total_all_chains_B": total_all / 1e9,
            "total_category_chains_B": total_cat_chains / 1e9,
            "defi_B": defi / 1e9,
            "cex_B": cex / 1e9,
            "bridge_B": bridge / 1e9,
            "payments_B": payments / 1e9,
            "other_cat_chains_B": other_cat / 1e9,
            "p2p_all_chains_B": p2p_all / 1e9,
        })

    df = pd.DataFrame(rows).set_index("date")
    save_csv(df, "usecase_decomposition.csv")

    # 5. Compute summary statistics
    totals = df.sum()
    total_all = totals["total_all_chains_B"]
    total_cat = totals["total_category_chains_B"]

    # Category shares (within category-supporting chains only)
    cat_shares = {}
    for cat in ["defi", "cex", "bridge", "payments", "other_cat_chains"]:
        key = f"{cat}_B"
        cat_shares[cat] = round(totals[key] / total_cat * 100, 1) if total_cat > 0 else 0

    # P2P share (all chains)
    p2p_share = round(totals["p2p_all_chains_B"] / total_all * 100, 1) if total_all > 0 else 0

    # Chain shares
    chain_shares = {}
    chain_total_sum = sum(s.sum() for s in chain_totals.values())
    for chain in CHAINS:
        if chain in chain_totals:
            chain_shares[chain] = round(chain_totals[chain].sum() / chain_total_sum * 100, 1)

    cat_chain_coverage = round(total_cat / total_all * 100, 1)

    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    print(f"\nTotal adjusted volume (all {len(chain_totals)} chains): ${total_all:,.0f}B")
    print(f"Category chains (ETH+SOL+BASE): ${total_cat:,.0f}B ({cat_chain_coverage}% of total)")
    print(f"\nApplication category shares (within ETH+SOL+BASE):")
    print(f"  {'Category':<25}{'Volume ($B)':<15}{'Share':<10}")
    print(f"  {'-'*50}")
    for cat in ["defi", "cex", "bridge", "payments", "other_cat_chains"]:
        vol = totals[f"{cat}_B"]
        print(f"  {cat:<25}{vol:>10,.0f}B    {cat_shares[cat]:>5.1f}%")
    print(f"  {'SUBTOTAL':<25}{total_cat:>10,.0f}B    100.0%")

    print(f"\nP2P transfers (all chains): ${totals['p2p_all_chains_B']:,.0f}B ({p2p_share}% of all-chain total)")

    print(f"\nChain volume shares:")
    for chain, share in sorted(chain_shares.items(), key=lambda x: -x[1]):
        print(f"  {chain:<12}{share:>5.1f}%")

    results = {
        "source": "Artemis API (data-svc.artemisxyz.com)",
        "period": f"{start} to {end}",
        "n_months": len(df),
        "total_adjusted_volume_all_chains_B": round(total_all, 0),
        "total_category_chains_B": round(total_cat, 0),
        "category_chain_coverage_pct": cat_chain_coverage,
        "application_category_shares_pct": cat_shares,
        "p2p_share_all_chains_pct": p2p_share,
        "chain_volume_shares_pct": chain_shares,
        "category_chains": CATEGORY_CHAINS,
        "all_chains": list(chain_totals.keys()),
        "methodology": (
            "Application categories (defi, cex, bridge, payments) from Artemis's "
            "ARTEMIS_STABLECOIN_TRANSFER_VOLUME endpoint with category-chain symbol syntax. "
            "Available for ETH, SOL, BASE only. P2P from separate P2P_STABLECOIN_TRANSFER_VOLUME "
            "endpoint across all chains. Artemis filtering removes intra-exchange transfers and MEV. "
            "Category shares computed within ETH+SOL+BASE only. P2P share computed across all chains."
        ),
    }

    # Paper sentence
    results["paper_sentence"] = (
        f"Artemis-filtered stablecoin transfer volume across nine chains totals "
        f"${total_all/1e3:,.0f} trillion over the sample period. "
        f"On the three chains with application-level categorization (Ethereum, Solana, Base, "
        f"representing {cat_chain_coverage} percent of total volume), "
        f"DeFi protocols account for {cat_shares['defi']} percent, "
        f"centralized exchanges for {cat_shares['cex']} percent, "
        f"and identified payments for {cat_shares['payments']} percent of adjusted transfer volume. "
        f"Peer-to-peer transfers, measured across all chains, constitute {p2p_share} percent "
        f"of total adjusted volume, with Tron ({chain_shares.get('tron', 0)} percent of chain volume) "
        f"dominated by P2P activity."
    )
    print(f"\nPaper sentence: {results['paper_sentence']}")

    save_json(results, "usecase_decomposition_results.json")
    print("\n✓ Done")


if __name__ == "__main__":
    main()
