"""Phase 1-4: Multi-chain gateway volume queries via Dune API.

Runs expanded queries for Ethereum (35 addresses), Tron, Solana, and Base.
Builds on the 08a_dune_queries.py infrastructure with the expanded gateway registry.
"""
import requests, pandas as pd, time, sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "config"))
from settings import DUNE_API_KEY, PRIMARY_START, PRIMARY_END
from gateway_registry import (
    ALL_GATEWAYS, STABLECOIN_CONTRACTS,
    get_gateways_by_chain, get_chain_summary,
)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_RAW, DATA_PROC, save_json, save_csv

DUNE_API = "https://api.dune.com/api/v1"
HEADERS = {"X-Dune-API-Key": DUNE_API_KEY, "Content-Type": "application/json"}


def create_query(name, sql):
    resp = requests.post(
        f"{DUNE_API}/query",
        headers=HEADERS,
        json={"name": f"gw_expansion_{name}", "query_sql": sql.strip(), "is_private": True},
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"    Create failed: {resp.status_code} {resp.text[:300]}")
        return None
    return resp.json().get("query_id")


def execute_query(query_id):
    resp = requests.post(
        f"{DUNE_API}/query/{query_id}/execute",
        headers=HEADERS,
        json={"performance": "medium"},
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"    Execute failed: {resp.status_code} {resp.text[:300]}")
        return None
    return resp.json().get("execution_id")


def poll_and_fetch(execution_id, max_polls=120, interval=10):
    for attempt in range(max_polls):
        time.sleep(interval)
        try:
            resp = requests.get(
                f"{DUNE_API}/execution/{execution_id}/status",
                headers=HEADERS, timeout=30,
            )
            if resp.status_code != 200:
                continue
            state = resp.json().get("state", "")
            if attempt % 3 == 0:
                print(f"    Poll {attempt + 1}: {state}")
            if state == "QUERY_STATE_COMPLETED":
                break
            elif state in ("QUERY_STATE_FAILED", "QUERY_STATE_CANCELLED"):
                print(f"    Query failed: {resp.json().get('error', 'unknown')}")
                return None
        except Exception as e:
            print(f"    Poll error: {e}")
    else:
        print("    Timed out")
        return None

    results_resp = requests.get(
        f"{DUNE_API}/execution/{execution_id}/results",
        headers=HEADERS, params={"limit": 500000}, timeout=120,
    )
    if results_resp.status_code != 200:
        print(f"    Results failed: {results_resp.status_code}")
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
    return df


# ── Build SQL for each chain ────────────────────────────────

def build_ethereum_expanded_sql():
    """Phase 1: Expanded Ethereum gateway query (~35 addresses)."""
    gw = get_gateways_by_chain("ethereum")
    values = ",\n        ".join(
        f"({a['address']}, '{a['entity']}', {a['tier']}, '{a['address_type']}')"
        for a in gw
    )
    return f"""
WITH gw AS (
    SELECT address, name, tier, addr_type FROM (VALUES
        {values}
    ) AS t(address, name, tier, addr_type)
)
SELECT date_trunc('day', e.evt_block_time) AS day,
    g.name AS entity, g.tier, g.addr_type,
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
GROUP BY 1, 2, 3, 4, 5
ORDER BY 1
"""


def build_tron_gateway_sql():
    """Phase 2: Tron gateway volume query."""
    gw = get_gateways_by_chain("tron")
    # Build CASE WHEN for each address
    when_from = "\n        ".join(
        f"WHEN \"from\" = '{a['address']}' THEN '{a['entity']}'"
        for a in gw
    )
    when_to = "\n        ".join(
        f"WHEN \"to\" = '{a['address']}' THEN '{a['entity']}'"
        for a in gw
    )
    addr_list = ", ".join(f"'{a['address']}'" for a in gw)
    tier_map = "\n        ".join(
        f"WHEN '{a['entity']}' THEN {a['tier']}"
        for a in gw
    )
    return f"""
SELECT
    date_trunc('day', block_time) AS day,
    COALESCE(
        CASE {when_from} ELSE NULL END,
        CASE {when_to} ELSE NULL END
    ) AS entity,
    CASE COALESCE(
        CASE {when_from} ELSE NULL END,
        CASE {when_to} ELSE NULL END
    )
        {tier_map}
    END AS tier,
    COUNT(*) AS n_transfers,
    SUM(amount) AS volume_usd
FROM tokens_tron.transfers
WHERE contract_address_varchar = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t'
AND block_time >= TIMESTAMP '{PRIMARY_START}'
AND ("from" IN ({addr_list}) OR "to" IN ({addr_list}))
GROUP BY 1, 2, 3
ORDER BY 1
"""


def build_solana_gateway_sql():
    """Phase 3: Solana gateway volume query."""
    gw = get_gateways_by_chain("solana")
    when_from = "\n        ".join(
        f"WHEN from_owner = '{a['address']}' THEN '{a['entity']}'"
        for a in gw
    )
    when_to = "\n        ".join(
        f"WHEN to_owner = '{a['address']}' THEN '{a['entity']}'"
        for a in gw
    )
    addr_list = ", ".join(f"'{a['address']}'" for a in gw)
    tier_map = "\n        ".join(
        f"WHEN '{a['entity']}' THEN {a['tier']}"
        for a in gw
    )
    return f"""
SELECT
    date_trunc('day', block_time) AS day,
    COALESCE(
        CASE {when_from} ELSE NULL END,
        CASE {when_to} ELSE NULL END
    ) AS entity,
    CASE COALESCE(
        CASE {when_from} ELSE NULL END,
        CASE {when_to} ELSE NULL END
    )
        {tier_map}
    END AS tier,
    CASE
        WHEN token_mint_address = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v' THEN 'USDC'
        WHEN token_mint_address = 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB' THEN 'USDT'
    END AS token,
    COUNT(*) AS n_transfers,
    SUM(amount) AS volume_usd
FROM tokens_solana.transfers
WHERE token_mint_address IN (
    'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
    'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB'
)
AND block_time >= TIMESTAMP '{PRIMARY_START}'
AND (from_owner IN ({addr_list}) OR to_owner IN ({addr_list}))
GROUP BY 1, 2, 3, 4
ORDER BY 1
"""


def build_base_gateway_sql():
    """Phase 4: Base gateway volume query."""
    gw = get_gateways_by_chain("base")
    values = ",\n        ".join(
        f"({a['address']}, '{a['entity']}', {a['tier']})"
        for a in gw
    )
    contracts = STABLECOIN_CONTRACTS["base"]
    contract_list = ", ".join(contracts.values())
    return f"""
WITH gw AS (
    SELECT address, name, tier FROM (VALUES
        {values}
    ) AS t(address, name, tier)
)
SELECT date_trunc('day', e.evt_block_time) AS day,
    g.name AS entity, g.tier,
    COUNT(*) AS n_transfers,
    SUM(CAST(e.value AS DOUBLE)) / 1e6 AS volume_usd
FROM erc20_base.evt_Transfer e
INNER JOIN gw g ON (e."from" = g.address OR e."to" = g.address)
WHERE e.contract_address IN ({contract_list})
AND e.evt_block_time >= TIMESTAMP '{PRIMARY_START}'
GROUP BY 1, 2, 3
ORDER BY 1
"""


def build_ethereum_total_expanded_sql():
    """Ethereum total volume (unchanged denominator for coverage ratio)."""
    return f"""
SELECT
    date_trunc('day', evt_block_time) AS day,
    CASE WHEN contract_address = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 THEN 'USDC'
         WHEN contract_address = 0xdAC17F958D2ee523a2206206994597C13D831ec7 THEN 'USDT' END AS token,
    COUNT(*) AS n_transfers,
    SUM(CAST(value AS DOUBLE)) / 1e6 AS volume_usd
FROM erc20_ethereum.evt_Transfer
WHERE contract_address IN (
    0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48,
    0xdAC17F958D2ee523a2206206994597C13D831ec7
)
AND evt_block_time >= TIMESTAMP '{PRIMARY_START}'
AND evt_block_time < TIMESTAMP '2026-02-01'
GROUP BY 1, 2
ORDER BY 1
"""


# ── Label discovery query (Phase 1A) ────────────────────────

def build_label_discovery_sql():
    """Discover labeled addresses from Dune's labels table for expansion."""
    return """
SELECT DISTINCT
    address, name, label_type
FROM labels.addresses
WHERE name ILIKE ANY(ARRAY[
    '%circle%', '%coinbase%', '%binance%',
    '%tether%', '%kraken%', '%okx%',
    '%gemini%', '%paxos%', '%bybit%',
    '%paypal%', '%bitgo%', '%robinhood%',
    '%htx%', '%huobi%', '%mexc%'
])
AND label_type IN ('exchange', 'fund', 'institution', 'contract')
AND blockchain = 'ethereum'
ORDER BY name
"""


def main():
    if not DUNE_API_KEY:
        print("ERROR: Set DUNE_API_KEY in config/settings.py")
        sys.exit(1)

    print("=" * 60)
    print("GATEWAY SCOPE EXPANSION: Multi-Chain Dune Queries")
    print("=" * 60)

    # Print registry summary
    summary = get_chain_summary()
    print("\nGateway Registry Summary:")
    for chain, counts in summary.items():
        print(f"  {chain}: {counts['total']} addresses "
              f"(T1={counts['tier1']}, T2={counts['tier2']}, T3={counts['tier3']})")
    print(f"  TOTAL: {sum(c['total'] for c in summary.values())} addresses")

    results = {}

    # Phase 1: Expanded Ethereum
    print("\n" + "=" * 60)
    print("PHASE 1: Expanded Ethereum Gateway Volume")
    print("=" * 60)
    try:
        df = run_query("eth_expanded_gw",
                       build_ethereum_expanded_sql(),
                       "dune_eth_expanded_gateway.csv")
        results["eth_expanded"] = "OK" if df is not None else "FAILED"
    except Exception as e:
        print(f"  ERROR: {e}")
        results["eth_expanded"] = f"ERROR: {e}"

    # Phase 1: Ethereum total (for coverage ratio)
    try:
        df = run_query("eth_total_v2",
                       build_ethereum_total_expanded_sql(),
                       "dune_eth_total_v2.csv")
        results["eth_total"] = "OK" if df is not None else "FAILED"
    except Exception as e:
        print(f"  ERROR: {e}")
        results["eth_total"] = f"ERROR: {e}"

    # Phase 1A: Label discovery
    print("\n" + "=" * 60)
    print("PHASE 1A: Label Discovery")
    print("=" * 60)
    try:
        df = run_query("label_discovery",
                       build_label_discovery_sql(),
                       "dune_label_discovery.csv")
        results["labels"] = "OK" if df is not None else "FAILED"
    except Exception as e:
        print(f"  ERROR: {e}")
        results["labels"] = f"ERROR: {e}"

    # Phase 2: Tron
    print("\n" + "=" * 60)
    print("PHASE 2: Tron Gateway Volume")
    print("=" * 60)
    try:
        df = run_query("tron_gw",
                       build_tron_gateway_sql(),
                       "dune_tron_gateway.csv")
        results["tron_gw"] = "OK" if df is not None else "FAILED"
    except Exception as e:
        print(f"  ERROR: {e}")
        results["tron_gw"] = f"ERROR: {e}"

    # Phase 3: Solana
    print("\n" + "=" * 60)
    print("PHASE 3: Solana Gateway Volume")
    print("=" * 60)
    try:
        df = run_query("solana_gw",
                       build_solana_gateway_sql(),
                       "dune_solana_gateway.csv")
        results["solana_gw"] = "OK" if df is not None else "FAILED"
    except Exception as e:
        print(f"  ERROR: {e}")
        results["solana_gw"] = f"ERROR: {e}"

    # Phase 4: Base
    print("\n" + "=" * 60)
    print("PHASE 4: Base Gateway Volume")
    print("=" * 60)
    try:
        df = run_query("base_gw",
                       build_base_gateway_sql(),
                       "dune_base_gateway.csv")
        results["base_gw"] = "OK" if df is not None else "FAILED"
    except Exception as e:
        print(f"  ERROR: {e}")
        results["base_gw"] = f"ERROR: {e}"

    # Summary
    print("\n" + "=" * 60)
    print("QUERY RESULTS:")
    for name, status in results.items():
        marker = "OK" if status == "OK" else "FAILED"
        print(f"  {name}: {marker}")

    save_json(results, "multichain_query_status.json")
    print("\n Done")


if __name__ == "__main__":
    main()
