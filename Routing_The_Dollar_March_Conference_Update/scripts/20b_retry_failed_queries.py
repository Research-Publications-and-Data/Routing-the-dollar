"""Retry failed Dune queries with corrected SQL.

Fixes:
1. Ethereum expanded: retry (transient Dune error)
2. Tron: use from_varchar/to_varchar columns (varchar, not varbinary)
3. Label discovery: skip (ILIKE not supported; labels table schema different)
"""
import requests, pandas as pd, time, sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "config"))
from settings import DUNE_API_KEY, PRIMARY_START, PRIMARY_END
from gateway_registry import get_gateways_by_chain
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_RAW, DATA_PROC, save_json

DUNE_API = "https://api.dune.com/api/v1"
HEADERS = {"X-Dune-API-Key": DUNE_API_KEY, "Content-Type": "application/json"}


def create_query(name, sql):
    resp = requests.post(
        f"{DUNE_API}/query", headers=HEADERS,
        json={"name": f"gw_retry_{name}", "query_sql": sql.strip(), "is_private": True},
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
            if attempt % 3 == 0:
                print(f"    Poll {attempt+1}: {state}")
            if state == "QUERY_STATE_COMPLETED":
                break
            elif state in ("QUERY_STATE_FAILED", "QUERY_STATE_CANCELLED"):
                print(f"    FAILED: {resp.json().get('error', 'unknown')}")
                return None
        except Exception as e:
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
        print(f"    Saved {len(df)} rows to {path}")
    else:
        print("    No data returned")
    return df


def build_ethereum_expanded_sql_v2():
    """Ethereum expanded — smaller batch to avoid timeout."""
    gw = get_gateways_by_chain("ethereum")
    values = ",\n        ".join(
        f"({a['address']}, '{a['entity']}', {a['tier']})"
        for a in gw
    )
    return f"""
WITH gw AS (
    SELECT address, name, tier FROM (VALUES
        {values}
    ) AS t(address, name, tier)
)
SELECT date_trunc('week', e.evt_block_time) AS week,
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


def build_tron_gateway_sql_v2():
    """Tron gateway — fixed: use from_varchar/to_varchar (varchar columns)."""
    gw = get_gateways_by_chain("tron")
    # Build address-to-entity mapping as a VALUES CTE using varchar
    values = ",\n        ".join(
        f"('{a['address']}', '{a['entity']}', {a['tier']})"
        for a in gw
    )
    return f"""
WITH gw AS (
    SELECT address, name, tier FROM (VALUES
        {values}
    ) AS t(address, name, tier)
)
SELECT
    date_trunc('week', t.block_time) AS week,
    COALESCE(gf.name, gt.name) AS entity,
    COALESCE(gf.tier, gt.tier) AS tier,
    COUNT(*) AS n_transfers,
    SUM(t.amount) AS volume_usd
FROM tokens_tron.transfers t
LEFT JOIN gw gf ON t.from_varchar = gf.address
LEFT JOIN gw gt ON t.to_varchar = gt.address
WHERE t.contract_address_varchar = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t'
AND t.block_time >= TIMESTAMP '{PRIMARY_START}'
AND (gf.address IS NOT NULL OR gt.address IS NOT NULL)
GROUP BY 1, 2, 3
ORDER BY 1
"""


def build_solana_gateway_sql_v2():
    """Solana gateway — use from_owner/to_owner (varchar columns)."""
    gw = get_gateways_by_chain("solana")
    values = ",\n        ".join(
        f"('{a['address']}', '{a['entity']}', {a['tier']})"
        for a in gw
    )
    return f"""
WITH gw AS (
    SELECT address, name, tier FROM (VALUES
        {values}
    ) AS t(address, name, tier)
)
SELECT
    date_trunc('week', t.block_time) AS week,
    COALESCE(gf.name, gt.name) AS entity,
    COALESCE(gf.tier, gt.tier) AS tier,
    CASE
        WHEN t.token_mint_address = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v' THEN 'USDC'
        WHEN t.token_mint_address = 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB' THEN 'USDT'
    END AS token,
    COUNT(*) AS n_transfers,
    SUM(t.amount) AS volume_usd
FROM tokens_solana.transfers t
LEFT JOIN gw gf ON t.from_owner = gf.address
LEFT JOIN gw gt ON t.to_owner = gt.address
WHERE t.token_mint_address IN (
    'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
    'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB'
)
AND t.block_time >= TIMESTAMP '{PRIMARY_START}'
AND (gf.address IS NOT NULL OR gt.address IS NOT NULL)
GROUP BY 1, 2, 3, 4
ORDER BY 1
"""


def build_base_gateway_sql_v2():
    """Base gateway — fixed contract addresses as hex literals."""
    gw = get_gateways_by_chain("base")
    values = ",\n        ".join(
        f"({a['address']}, '{a['entity']}', {a['tier']})"
        for a in gw
    )
    return f"""
WITH gw AS (
    SELECT address, name, tier FROM (VALUES
        {values}
    ) AS t(address, name, tier)
)
SELECT date_trunc('week', e.evt_block_time) AS week,
    g.name AS entity, g.tier,
    COUNT(*) AS n_transfers,
    SUM(CAST(e.value AS DOUBLE)) / 1e6 AS volume_usd
FROM erc20_base.evt_Transfer e
INNER JOIN gw g ON (e."from" = g.address OR e."to" = g.address)
WHERE e.contract_address IN (
    0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913,
    0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA
)
AND e.evt_block_time >= TIMESTAMP '{PRIMARY_START}'
GROUP BY 1, 2, 3
ORDER BY 1
"""


def main():
    if not DUNE_API_KEY:
        print("ERROR: Set DUNE_API_KEY in config/settings.py")
        sys.exit(1)

    print("=" * 60)
    print("RETRY FAILED QUERIES (corrected SQL)")
    print("=" * 60)
    results = {}

    # 1. Retry Ethereum expanded (weekly aggregation to reduce output)
    print("\n--- Ethereum Expanded (weekly, retry) ---")
    df = run_query("eth_expanded_v2", build_ethereum_expanded_sql_v2(),
                   "dune_eth_expanded_gateway.csv")
    results["eth_expanded"] = "OK" if df is not None else "FAILED"

    # 2. Tron (fixed varchar handling)
    print("\n--- Tron Gateway (fixed) ---")
    df = run_query("tron_gw_v2", build_tron_gateway_sql_v2(),
                   "dune_tron_gateway.csv")
    results["tron_gw"] = "OK" if df is not None else "FAILED"

    # 3. Solana (fixed from_owner/to_owner)
    print("\n--- Solana Gateway (fixed) ---")
    df = run_query("solana_gw_v2", build_solana_gateway_sql_v2(),
                   "dune_solana_gateway.csv")
    results["solana_gw"] = "OK" if df is not None else "FAILED"

    # 4. Base
    print("\n--- Base Gateway ---")
    df = run_query("base_gw_v2", build_base_gateway_sql_v2(),
                   "dune_base_gateway.csv")
    results["base_gw"] = "OK" if df is not None else "FAILED"

    print("\n" + "=" * 60)
    print("RESULTS:")
    for name, status in results.items():
        print(f"  {name}: {status}")
    save_json(results, "multichain_retry_status.json")


if __name__ == "__main__":
    main()
