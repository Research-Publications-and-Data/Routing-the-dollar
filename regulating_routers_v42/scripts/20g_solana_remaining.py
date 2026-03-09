"""Solana remaining entities: Binance, Kraken, OKX + Tether 2025.

Uses primary API key. One query per entity (full date range) to minimize
query creation count (avoids 'max private queries' limit).
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

# Only entities we still need
REMAINING = {
    "Binance": {"start": PRIMARY_START, "end": "2026-02-01"},
    "Kraken": {"start": PRIMARY_START, "end": "2026-02-01"},
    "OKX": {"start": PRIMARY_START, "end": "2026-02-01"},
    "Tether": {"start": "2025-01-01", "end": "2026-02-01"},  # only 2025+ missing
}


def create_query(name, sql):
    resp = requests.post(
        f"{DUNE_API}/query", headers=HEADERS,
        json={"name": f"sol_rem_{name}", "query_sql": sql.strip(), "is_private": True},
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


def build_entity_sql(entity_name, address, start, end):
    return f"""
SELECT
    date_trunc('month', block_time) AS month,
    '{entity_name}' AS entity,
    CASE
        WHEN token_mint_address = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v' THEN 'USDC'
        WHEN token_mint_address = 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB' THEN 'USDT'
    END AS token,
    COUNT(*) AS n_transfers,
    SUM(amount) AS volume_raw
FROM tokens_solana.transfers
WHERE token_mint_address IN (
    'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
    'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB'
)
AND block_time >= TIMESTAMP '{start}'
AND block_time < TIMESTAMP '{end}'
AND (from_owner = '{address}' OR to_owner = '{address}')
GROUP BY 1, 2, 3
ORDER BY 1
"""


def main():
    if not DUNE_API_KEY:
        print("ERROR: Set DUNE_API_KEY"); sys.exit(1)

    print("=" * 60)
    print("SOLANA REMAINING ENTITIES (primary key)")
    print("=" * 60)

    gateways = get_gateways_by_chain("solana")
    results = {}
    new_frames = []

    for entity, params in REMAINING.items():
        addrs = [g["address"] for g in gateways if g["entity"] == entity]
        tier = next((g["tier"] for g in gateways if g["entity"] == entity), 2)
        if not addrs:
            print(f"\n  {entity}: No address in registry, skipping")
            continue

        address = addrs[0]  # Single address per entity on Solana
        label = entity.lower().replace(" ", "_")
        print(f"\n--- {entity} (Tier {tier}, addr={address[:12]}...) ---")
        print(f"    Range: {params['start']} → {params['end']}")

        sql = build_entity_sql(entity, address, params["start"], params["end"])
        qid = create_query(label, sql)
        if not qid:
            results[entity] = "CREATE_FAILED"
            continue
        print(f"    Query ID: {qid}")
        eid = execute_query(qid)
        if not eid:
            results[entity] = "EXECUTE_FAILED"
            continue
        print(f"    Execution ID: {eid}")
        df = poll_and_fetch(eid)
        if df is not None and len(df) > 0:
            for col in ["volume_raw", "n_transfers"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            df["tier"] = tier
            df["volume_usd"] = df["volume_raw"] / 1e6
            # Save per-entity
            df.to_csv(DATA_RAW / f"dune_sol_{label}_new.csv", index=False)
            new_frames.append(df)
            total_vol = df["volume_usd"].sum()
            print(f"    OK: {len(df)} rows, ${total_vol:,.0f}")
            results[entity] = f"OK ({len(df)} rows)"
        else:
            print("    No data returned")
            results[entity] = "NO_DATA"

    # Merge with existing Solana data
    print("\n--- Merging with existing Solana data ---")
    try:
        existing = pd.read_csv(DATA_RAW / "dune_solana_gateway.csv")
        for col in ["volume_raw", "n_transfers", "volume_usd"]:
            if col in existing.columns:
                existing[col] = pd.to_numeric(existing[col], errors="coerce")
        all_frames = [existing] + new_frames
    except FileNotFoundError:
        all_frames = new_frames

    if all_frames:
        merged = pd.concat(all_frames, ignore_index=True)
        # Deduplicate (same entity+month+token): keep latest
        if "month" in merged.columns:
            merged = merged.sort_values("volume_usd", ascending=False).drop_duplicates(
                subset=["entity", "month", "token"], keep="first")
        path = DATA_RAW / "dune_solana_gateway.csv"
        merged.to_csv(path, index=False)
        print(f"  Merged Solana: {len(merged)} rows, {merged['entity'].nunique()} entities")
        print(f"  Total volume: ${merged['volume_usd'].sum():,.0f}")

    print("\n" + "=" * 60)
    print("RESULTS:")
    for name, status in results.items():
        print(f"  {name}: {status}")
    save_json(results, "solana_remaining_status.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
