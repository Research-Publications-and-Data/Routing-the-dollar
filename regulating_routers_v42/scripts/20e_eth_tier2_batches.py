"""ETH Tier 2 expansion: split into sub-batches to avoid Dune transient errors.

Batch A: Binance (5 addresses — highest volume, most likely to cause issues)
Batch B: Tether + Kraken (4 addresses)
Batch C: OKX + Bybit + Robinhood (4 addresses)
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

# Sub-batch definitions for Tier 2
BATCHES = {
    "t2_binance": ["Binance"],
    "t2_tether_kraken": ["Tether", "Kraken"],
    "t2_okx_bybit_robin": ["OKX", "Bybit", "Robinhood"],
}


def create_query(name, sql):
    resp = requests.post(
        f"{DUNE_API}/query", headers=HEADERS,
        json={"name": f"gw_t2_{name}", "query_sql": sql.strip(), "is_private": True},
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


def poll_and_fetch(execution_id, max_polls=150, interval=10):
    for attempt in range(max_polls):
        time.sleep(interval)
        try:
            resp = requests.get(f"{DUNE_API}/execution/{execution_id}/status",
                                headers=HEADERS, timeout=30)
            if resp.status_code != 200:
                continue
            state = resp.json().get("state", "")
            if attempt % 3 == 0:
                print(f"    Poll {attempt+1}: {state}")
            if state == "QUERY_STATE_COMPLETED":
                break
            elif state in ("QUERY_STATE_FAILED", "QUERY_STATE_CANCELLED"):
                err = resp.json().get("error", "unknown")
                print(f"    FAILED: {err}")
                return None
        except Exception as e:
            print(f"    Poll error: {e}")
    else:
        print("    Timed out after max polls")
        return None
    results_resp = requests.get(f"{DUNE_API}/execution/{execution_id}/results",
                                headers=HEADERS, params={"limit": 500000}, timeout=120)
    if results_resp.status_code != 200:
        return None
    rows = results_resp.json().get("result", {}).get("rows", [])
    return pd.DataFrame(rows) if rows else None


def build_batch_sql(entities):
    """Build SQL for a subset of Tier 2 ETH addresses."""
    all_t2 = [a for a in get_gateways_by_chain("ethereum") if a["tier"] == 2]
    batch_addrs = [a for a in all_t2 if a["entity"] in entities]
    if not batch_addrs:
        return None
    values = ",\n        ".join(
        f"({a['address']}, '{a['entity']}', {a['tier']})"
        for a in batch_addrs
    )
    return f"""
WITH gw AS (
    SELECT address, name, tier FROM (VALUES
        {values}
    ) AS t(address, name, tier)
)
SELECT date_trunc('month', e.evt_block_time) AS month,
    g.name AS entity, g.tier,
    CASE WHEN e.contract_address = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 THEN 'USDC'
         WHEN e.contract_address = 0xdAC17F958D2ee523a2206206994597C13D831ec7 THEN 'USDT' END AS token,
    COUNT(*) AS n_transfers,
    SUM(CAST(e.value AS DOUBLE)) / 1e6 AS volume_usd
FROM erc20_ethereum.evt_Transfer e
INNER JOIN gw g ON (e."from" = g.address OR e."to" = g.address)
WHERE e.contract_address IN (
    0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48,
    0xdAC17F958D2ee523a2206206994597C13D831ec7
)
AND e.evt_block_time >= TIMESTAMP '{PRIMARY_START}'
AND e.evt_block_time < TIMESTAMP '2026-02-01'
GROUP BY 1, 2, 3, 4
ORDER BY 1
"""


def run_query(name, sql, output_file):
    print(f"\n  [{name}]")
    qid = create_query(name, sql)
    if not qid:
        return None
    print(f"    Query ID: {qid}")
    eid = execute_query(qid)
    if not eid:
        return None
    print(f"    Execution ID: {eid}")
    df = poll_and_fetch(eid)
    if df is not None and len(df) > 0:
        path = DATA_RAW / output_file
        df.to_csv(path, index=False)
        print(f"    OK: {len(df)} rows saved to {path}")
    else:
        print("    No data returned")
    return df


def main():
    if not DUNE_API_KEY:
        print("ERROR: Set DUNE_API_KEY"); sys.exit(1)

    print("=" * 60)
    print("ETH TIER 2 SUB-BATCH QUERIES")
    print("=" * 60)
    results = {}
    all_frames = []

    for batch_name, entities in BATCHES.items():
        n_addrs = len([a for a in get_gateways_by_chain("ethereum")
                       if a["tier"] == 2 and a["entity"] in entities])
        print(f"\n--- {batch_name}: {', '.join(entities)} ({n_addrs} addrs) ---")
        sql = build_batch_sql(entities)
        if sql is None:
            results[batch_name] = "SKIPPED"
            continue
        df = run_query(batch_name, sql, f"dune_eth_{batch_name}.csv")
        if df is not None:
            results[batch_name] = f"OK ({len(df)} rows)"
            all_frames.append(df)
        else:
            results[batch_name] = "FAILED"

    # Combine all Tier 2 sub-batches
    if all_frames:
        combined = pd.concat(all_frames, ignore_index=True)
        path = DATA_RAW / "dune_eth_tier2_gateway.csv"
        combined.to_csv(path, index=False)
        print(f"\n  Combined Tier 2: {len(combined)} rows saved to {path}")
        results["tier2_combined"] = f"OK ({len(combined)} rows)"

        # Also rebuild the full expanded ETH file (all tiers)
        full_frames = [combined]
        for tier_file in ["dune_eth_tier1_gateway.csv", "dune_eth_tier3_gateway.csv"]:
            try:
                t = pd.read_csv(DATA_RAW / tier_file)
                full_frames.append(t)
            except FileNotFoundError:
                pass
        if len(full_frames) > 1:
            full = pd.concat(full_frames, ignore_index=True)
            path = DATA_RAW / "dune_eth_expanded_gateway.csv"
            full.to_csv(path, index=False)
            print(f"  Full expanded ETH: {len(full)} rows (all 3 tiers)")
    else:
        results["tier2_combined"] = "FAILED"

    print("\n" + "=" * 60)
    print("RESULTS:")
    for name, status in results.items():
        print(f"  {name}: {status}")
    save_json(results, "eth_tier2_batch_status.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
