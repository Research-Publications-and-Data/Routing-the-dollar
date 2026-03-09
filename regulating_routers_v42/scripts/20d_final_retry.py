"""Final retry: ETH Tier 2 (transient error) + Solana (split by year to reduce memory)."""
import requests, pandas as pd, time, sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "config"))
from settings import DUNE_API_KEY, PRIMARY_START
from gateway_registry import get_gateways_by_chain
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_RAW, DATA_PROC, save_json

DUNE_API = "https://api.dune.com/api/v1"
HEADERS = {"X-Dune-API-Key": DUNE_API_KEY, "Content-Type": "application/json"}


def create_query(name, sql):
    resp = requests.post(
        f"{DUNE_API}/query", headers=HEADERS,
        json={"name": f"gw_final_{name}", "query_sql": sql.strip(), "is_private": True},
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
        print("    Timed out")
        return None
    results_resp = requests.get(f"{DUNE_API}/execution/{execution_id}/results",
                                headers=HEADERS, params={"limit": 500000}, timeout=120)
    if results_resp.status_code != 200:
        return None
    rows = results_resp.json().get("result", {}).get("rows", [])
    return pd.DataFrame(rows) if rows else None


def run_query(name, sql, output_file=None):
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
        if output_file:
            path = DATA_RAW / output_file
            df.to_csv(path, index=False)
            print(f"    Saved {len(df)} rows to {path}")
    else:
        print("    No data returned")
    return df


def build_eth_tier2_sql():
    """ETH Tier 2 addresses, monthly aggregation."""
    gw = [a for a in get_gateways_by_chain("ethereum") if a["tier"] == 2]
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


def build_solana_year_sql(year_start, year_end):
    """Solana query for a single year range — reduces memory."""
    gw = get_gateways_by_chain("solana")
    # Only Tier 1+2 (6 addresses) to reduce join complexity
    gw_filtered = [a for a in gw if a["tier"] <= 2]
    values = ",\n        ".join(
        f"('{a['address']}', '{a['entity']}', {a['tier']})"
        for a in gw_filtered
    )
    return f"""
WITH gw AS (
    SELECT address, name, tier FROM (VALUES
        {values}
    ) AS t(address, name, tier)
)
SELECT
    date_trunc('month', t.block_time) AS month,
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
AND t.block_time >= TIMESTAMP '{year_start}'
AND t.block_time < TIMESTAMP '{year_end}'
AND (gf.address IS NOT NULL OR gt.address IS NOT NULL)
GROUP BY 1, 2, 3, 4
ORDER BY 1
"""


def build_solana_tier3_sql():
    """Solana Tier 3 (DeFi protocols) — separate smaller query."""
    gw = [a for a in get_gateways_by_chain("solana") if a["tier"] == 3]
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
    date_trunc('month', t.block_time) AS month,
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
AND t.block_time < TIMESTAMP '2026-02-01'
AND (gf.address IS NOT NULL OR gt.address IS NOT NULL)
GROUP BY 1, 2, 3, 4
ORDER BY 1
"""


def main():
    if not DUNE_API_KEY:
        print("ERROR: Set DUNE_API_KEY"); sys.exit(1)

    print("=" * 60)
    print("FINAL RETRY: ETH Tier 2 + Solana (split by year)")
    print("=" * 60)
    results = {}

    # ── ETH Tier 2 retry ─────────────────────────────────
    print("\n--- ETH Tier 2 (13 addresses, retry) ---")
    df = run_query("eth_t2_retry", build_eth_tier2_sql(), "dune_eth_tier2_gateway.csv")
    results["eth_tier2"] = "OK" if df is not None else "FAILED"

    # Recombine all ETH tiers if Tier 2 succeeded
    if df is not None:
        frames = []
        for tier_file in ["dune_eth_tier1_gateway.csv", "dune_eth_tier2_gateway.csv", "dune_eth_tier3_gateway.csv"]:
            try:
                t = pd.read_csv(DATA_RAW / tier_file)
                frames.append(t)
            except FileNotFoundError:
                pass
        if frames:
            combined = pd.concat(frames, ignore_index=True)
            path = DATA_RAW / "dune_eth_expanded_gateway.csv"
            combined.to_csv(path, index=False)
            print(f"\n  Recombined ETH: {len(combined)} rows")

    # ── Solana by year (Tier 1+2 only) ───────────────────
    sol_frames = []
    for year_start, year_end, label in [
        ("2023-02-01", "2024-01-01", "2023"),
        ("2024-01-01", "2025-01-01", "2024"),
        ("2025-01-01", "2026-02-01", "2025"),
    ]:
        print(f"\n--- Solana T1+T2 {label} ---")
        df = run_query(f"solana_t12_{label}", build_solana_year_sql(year_start, year_end))
        results[f"solana_{label}"] = "OK" if df is not None else "FAILED"
        if df is not None:
            sol_frames.append(df)

    # Solana Tier 3 separately
    print(f"\n--- Solana Tier 3 (DeFi protocols) ---")
    df = run_query("solana_t3", build_solana_tier3_sql())
    results["solana_tier3"] = "OK" if df is not None else "FAILED"
    if df is not None:
        sol_frames.append(df)

    # Combine Solana
    if sol_frames:
        combined = pd.concat(sol_frames, ignore_index=True)
        path = DATA_RAW / "dune_solana_gateway.csv"
        combined.to_csv(path, index=False)
        print(f"\n  Combined Solana: {len(combined)} rows saved to {path}")
        results["solana_combined"] = "OK"
    else:
        results["solana_combined"] = "FAILED"

    print("\n" + "=" * 60)
    print("RESULTS:")
    for name, status in results.items():
        print(f"  {name}: {status}")
    save_json(results, "final_retry_status.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
