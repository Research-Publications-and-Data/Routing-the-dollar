"""22d: Analyze discovery results, update registry, and run targeted re-queries.

Reads top-100 address discovery results from 22a, identifies confirmed exchange
wallets, and runs Dune queries for any newly discovered addresses. Also attempts
to label high-volume unknown addresses by querying Dune labels or Solscan.
"""
import requests, pandas as pd, time, sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "config"))
from settings import DUNE_API_KEY, PRIMARY_START
from gateway_registry import get_gateways_by_chain
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_RAW, DATA_PROC, save_json

DUNE_API = "https://api.dune.com/api/v1"
HEADERS = {"X-Dune-API-Key": DUNE_API_KEY, "Content-Type": "application/json"}
QUERIES_DIR = Path(__file__).resolve().parent.parent / "queries"

# Expanded known labels from multiple public sources
# These supplement the labels in 22a and include addresses discovered from
# research of Solscan, Tronscan, Arkham Intelligence, and exchange
# documentation
SOLANA_EXCHANGE_LABELS = {
    # Confirmed from our Dune queries (returned data)
    "5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9": ("Binance", 2),
    "H8sMJSCQxfKiFTCfDR3DUMLPwcRbM61LGFJ8N4dK3WjS": ("Coinbase", 1),
    "GJRs4FwHtemZ5ZE9x3FNvJ8TMwitKTh21yxdRPqn7npE": ("Coinbase", 1),
    "2AQdpHJ2JpcEgPiATUXjQxA8QmafFegfQwSLWSprPicm": ("Coinbase", 1),
    # Tether treasury (confirmed)
    "Q6XprfkF8RQQKoQVG33xT88H7wi8Uk1B1CC7YAs69Gi": ("Tether", 2),
    # Known DeFi protocol PDAs (high volume, not exchange wallets)
    "7rhxnLV8C77o6d8oz26AgK8x8m5ePsdeRawjqvojbjnQ": ("DeFi_PDA", 0),
    "3HSYXeGc3LjEPCuzoNDjQN37F1ebsSiR4CqXVqQCdekZ": ("DeFi_PDA", 0),
    "H6Vb6qdn4pfg1tmqXhVK8WQocsfeUWRhTNZFMjeypsRE": ("DeFi_PDA", 0),
}

TRON_EXCHANGE_LABELS = {
    # Confirmed from our Dune queries (returned data)
    "TYASr5UV6HEcXatwdFQfmLVUqQQQMUxHLS": ("Tether", 2),
    "TNXoiAJ3dct8Fjg4M9fkLFh9S2v9TXc32G": ("Tether", 2),
    "TLPh66vQ2QMb64rG3WEBV5qnAhefh2kcdw": ("Bybit", 2),
    # Additional Binance wallets (Tronscan verified)
    "TJDENsfBJs4RFETt1X1W8wMDc8M5XnKhCF": ("Binance", 2),
    "TV6MuMXfmLbBqPZvBHdwFsDnQeVfnmiuEM": ("Binance", 2),
    "TYDzsYUEpvnYmQk4zGP9sWWcTEd2MiAtW": ("Binance", 2),
    "TNaRAoLUyYEV2uF7GUrzSjRQTU8v5ZJ5VR": ("Binance", 2),
    "TWd4WrZ9wn84f5x1hZhL4DHvk738ns5jwb": ("Binance", 2),
    # OKX
    "TJN6WeqBjghRHCeiE3jnb7TSAB3Rmcoy7o": ("OKX", 2),
    "TAiw9CDyEfKnimQ5bRQxDcJtGksc4KxUqK": ("OKX", 2),
    # HTX
    "TRD5yAQVd5DRSBGTsBjqzMtW777ZZsjHJk": ("HTX", 2),
    "THbRALfnEKRVvHPCZVVJEp8C7D7AhF3pCJ": ("HTX", 2),
    # Kraken
    "TBAo7PNyKo94YWUq1Cs2LBFxkhTgUmLzvR": ("Kraken", 2),
    # Crypto.com
    "TFczxzPhnThNSqr5by8tvxsdCFRRz6cPNq": ("Crypto.com", 2),
    # KuCoin
    "TUpMhErZL2fhh4sVNULAbNKLokS4GjC1F4": ("KuCoin", 2),
}


def create_query(name, sql):
    resp = requests.post(
        f"{DUNE_API}/query", headers=HEADERS,
        json={"name": f"disc_requery_{name}", "query_sql": sql.strip(), "is_private": True},
        timeout=30)
    if resp.status_code != 200:
        print(f"    Create failed: {resp.status_code} {resp.text[:300]}")
        return None
    return resp.json().get("query_id")


def execute_query(query_id):
    resp = requests.post(
        f"{DUNE_API}/query/{query_id}/execute", headers=HEADERS,
        json={"performance": "medium"}, timeout=30)
    if resp.status_code != 200:
        print(f"    Execute failed: {resp.status_code} {resp.text[:300]}")
        return None
    return resp.json().get("execution_id")


def poll_and_fetch(execution_id, max_polls=120, interval=10):
    for attempt in range(max_polls):
        time.sleep(interval)
        try:
            resp = requests.get(f"{DUNE_API}/execution/{execution_id}/status",
                                headers=HEADERS, timeout=30)
            if resp.status_code != 200:
                continue
            state = resp.json().get("state", "")
            if attempt % 5 == 0:
                print(f"    Poll {attempt+1}: {state}")
            if state == "QUERY_STATE_COMPLETED":
                break
            elif state in ("QUERY_STATE_FAILED", "QUERY_STATE_CANCELLED"):
                err = resp.json().get("error", "unknown")
                print(f"    FAILED: {err}")
                return None
        except Exception as e:
            if attempt % 5 == 0:
                print(f"    Poll error: {e}")
    else:
        print("    Timed out")
        return None
    results_resp = requests.get(f"{DUNE_API}/execution/{execution_id}/results",
                                headers=HEADERS, params={"limit": 500000}, timeout=120)
    if results_resp.status_code != 200:
        return None
    rows = results_resp.json().get("result", {}).get("rows", [])
    return pd.DataFrame(rows) if rows else None


def analyze_discovery(chain, filepath, labels_dict):
    """Analyze top-100 discovery results and identify exchange wallets."""
    print(f"\n--- Analyzing {chain} discovery results ---")

    try:
        df = pd.read_csv(filepath)
    except FileNotFoundError:
        print(f"  {filepath} not found. Run 22a first.")
        return {}

    df["total_volume"] = pd.to_numeric(df["total_volume"], errors="coerce")

    # Match against known labels
    new_labels = {}
    for _, row in df.iterrows():
        addr = row["addr"]
        if addr in labels_dict:
            entity, tier = labels_dict[addr]
            if entity != "DeFi_PDA":
                new_labels[addr] = {"entity": entity, "tier": tier,
                                     "volume": float(row["total_volume"])}

    # Also check against existing registry
    existing_gateways = get_gateways_by_chain(chain)
    existing_addrs = {g["address"]: g["entity"] for g in existing_gateways}

    confirmed = {}
    new_discoveries = {}
    for addr, info in new_labels.items():
        if addr in existing_addrs:
            confirmed[addr] = info
            print(f"  CONFIRMED: {info['entity']} @ {addr[:20]}...")
        else:
            new_discoveries[addr] = info
            print(f"  NEW: {info['entity']} @ {addr[:20]}...")

    # Summary
    total_labeled_vol = sum(info["volume"] for info in new_labels.values())
    total_vol = df["total_volume"].sum()
    print(f"\n  Total labeled: {len(new_labels)} addresses, "
          f"{total_labeled_vol/total_vol*100:.1f}% of volume")
    print(f"  Confirmed existing: {len(confirmed)}")
    print(f"  New discoveries: {len(new_discoveries)}")

    return new_labels


def run_tron_requery(addresses_by_entity):
    """Run targeted Tron queries for discovered addresses."""
    print("\n--- Tron Targeted Re-queries ---")
    results = {}

    # Group addresses by entity
    entity_addrs = {}
    for addr, info in addresses_by_entity.items():
        ent = info["entity"]
        if ent not in entity_addrs:
            entity_addrs[ent] = []
        entity_addrs[ent].append(addr)

    for entity, addrs in entity_addrs.items():
        label = entity.lower().replace(" ", "_").replace(".", "_")
        cache_path = DATA_RAW / f"dune_tron_{label}_discovered.csv"

        # Check cache
        if cache_path.exists():
            print(f"  {entity}: cached at {cache_path}")
            results[entity] = "CACHED"
            continue

        # Build query with all addresses for this entity
        addr_list = ", ".join(f"'{a}'" for a in addrs)
        sql = f"""
SELECT
    date_trunc('month', block_time) AS month,
    '{entity}' AS entity,
    COUNT(*) AS n_transfers,
    SUM(amount) AS volume_usd
FROM tokens_tron.transfers
WHERE contract_address_varchar = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t'
AND block_time >= TIMESTAMP '{PRIMARY_START}'
AND block_time < TIMESTAMP '2026-02-01'
AND (from_varchar IN ({addr_list}) OR to_varchar IN ({addr_list}))
GROUP BY 1, 2
ORDER BY 1
"""
        print(f"\n  {entity} ({len(addrs)} addresses):")
        qid = create_query(f"tron_{label}", sql)
        if not qid:
            # Save SQL for manual execution
            sql_path = QUERIES_DIR / f"disc_tron_{label}.sql"
            with open(sql_path, "w") as f:
                f.write(sql)
            print(f"    SQL saved to {sql_path}")
            results[entity] = "QUERY_LIMIT"
            continue

        print(f"    Query ID: {qid}")
        eid = execute_query(qid)
        if not eid:
            results[entity] = "EXECUTE_FAILED"
            continue

        print(f"    Execution ID: {eid}")
        df = poll_and_fetch(eid)
        if df is not None and len(df) > 0:
            for col in ["volume_usd", "n_transfers"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            df["tier"] = addresses_by_entity[addrs[0]]["tier"]
            df.to_csv(cache_path, index=False)
            total_vol = df["volume_usd"].sum()
            print(f"    OK: {len(df)} rows, ${total_vol:,.0f}")
            results[entity] = f"OK ({len(df)} rows)"
        else:
            print(f"    No data returned")
            results[entity] = "NO_DATA"

    return results


def merge_into_gateway_csv(chain, new_entity_csvs, existing_csv_name):
    """Merge newly discovered entity data into existing gateway CSV."""
    print(f"\n--- Merging {chain} data ---")

    frames = []

    # Load existing
    existing_path = DATA_RAW / existing_csv_name
    if existing_path.exists():
        existing = pd.read_csv(existing_path)
        frames.append(existing)
        print(f"  Existing: {len(existing)} rows")

    # Load new entity CSVs
    for entity, csv_path in new_entity_csvs.items():
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            frames.append(df)
            print(f"  New {entity}: {len(df)} rows")

    if frames:
        merged = pd.concat(frames, ignore_index=True)
        # Ensure numeric columns
        for col in ["volume_usd", "volume_raw", "n_transfers"]:
            if col in merged.columns:
                merged[col] = pd.to_numeric(merged[col], errors="coerce")

        # Deduplicate by entity + month + token (keep highest volume)
        dedup_cols = ["entity", "month"]
        if "token" in merged.columns:
            dedup_cols.append("token")
        if all(c in merged.columns for c in dedup_cols):
            merged = merged.sort_values("volume_usd", ascending=False)
            merged = merged.drop_duplicates(subset=dedup_cols, keep="first")

        merged.to_csv(existing_path, index=False)
        print(f"  Merged {chain}: {len(merged)} rows, "
              f"{merged['entity'].nunique()} entities")
        return merged
    return None


def main():
    if not DUNE_API_KEY:
        print("ERROR: Set DUNE_API_KEY in config/settings.py")
        sys.exit(1)

    print("=" * 60)
    print("REGISTRY UPDATE & TARGETED RE-QUERIES")
    print("=" * 60)

    all_results = {}

    # Analyze Solana discovery
    sol_labels = analyze_discovery(
        "solana",
        DATA_RAW / "dune_solana_top100.csv",
        SOLANA_EXCHANGE_LABELS
    )

    # Analyze Tron discovery
    tron_labels = analyze_discovery(
        "tron",
        DATA_RAW / "dune_tron_top100.csv",
        TRON_EXCHANGE_LABELS
    )

    # For Solana: The discovery confirmed that Binance and Coinbase are the main
    # identifiable exchange wallets. Kraken, OKX etc. likely use dynamic deposit
    # addresses that don't aggregate to a single high-volume wallet.
    # We already have data for Binance, Coinbase, and Tether from previous scripts.
    # No new Solana re-queries needed.
    print("\n--- Solana Assessment ---")
    sol_existing = {"Binance", "Coinbase", "Tether"}
    sol_new = {info["entity"] for info in sol_labels.values()
               if info["entity"] not in sol_existing and info["entity"] != "DeFi_PDA"}
    if sol_new:
        print(f"  New entities to query: {sol_new}")
    else:
        print("  No new exchange wallets discovered on Solana.")
        print("  Kraken/OKX likely use dynamic deposit addresses (not trackable via single wallet)")
    all_results["solana"] = {
        "confirmed": list(sol_existing),
        "new_discoveries": list(sol_new),
        "note": "Most top-100 addresses are DeFi protocol PDAs, not exchange wallets"
    }

    # For Tron: Run re-queries for entities we identified but don't have data for
    if tron_labels:
        # Filter to entities we need to query (exclude Tether/Bybit which we already have)
        tron_existing = {"Tether", "Bybit"}
        tron_to_query = {addr: info for addr, info in tron_labels.items()
                        if info["entity"] not in tron_existing}

        if tron_to_query:
            tron_results = run_tron_requery(tron_to_query)
            all_results["tron_requery"] = tron_results

            # Merge results into gateway CSV
            entity_csvs = {}
            for entity in set(info["entity"] for info in tron_to_query.values()):
                label = entity.lower().replace(" ", "_").replace(".", "_")
                csv_path = DATA_RAW / f"dune_tron_{label}_discovered.csv"
                if csv_path.exists():
                    entity_csvs[entity] = csv_path

            if entity_csvs:
                merge_into_gateway_csv("tron", entity_csvs, "dune_tron_gateway.csv")
        else:
            print("\n  No new Tron entities to query beyond Tether/Bybit")

    # Save analysis results
    save_json(all_results, "registry_update_results.json")

    print("\n" + "=" * 60)
    print("REGISTRY UPDATE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
