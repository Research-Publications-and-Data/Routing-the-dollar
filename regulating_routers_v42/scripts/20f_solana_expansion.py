"""Solana gateway expansion: individual address queries to avoid memory limits.

Previous attempts failed with "Query exceeds cluster capacity" even when:
- Split by year (2023/2024/2025)
- Limited to Tier 1+2 (6 addresses)
- Using LEFT JOIN approach

New strategy:
- Query each address individually (or in pairs by entity)
- Use WHERE clause filtering instead of JOIN
- Quarterly time windows
- Alternate Dune API key with potentially different capacity
"""
import os, requests, pandas as pd, time, sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "config"))
from settings import PRIMARY_START
from gateway_registry import get_gateways_by_chain
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_RAW, DATA_PROC, save_json

# Dune API key — set via environment variable or config/settings.py
DUNE_API_KEY = os.environ.get("DUNE_API_KEY", "")
DUNE_API = "https://api.dune.com/api/v1"
HEADERS = {"X-Dune-API-Key": DUNE_API_KEY, "Content-Type": "application/json"}

# Quarter boundaries for splitting
QUARTERS = [
    ("2023-02-01", "2023-07-01", "2023H1"),
    ("2023-07-01", "2024-01-01", "2023H2"),
    ("2024-01-01", "2024-07-01", "2024H1"),
    ("2024-07-01", "2025-01-01", "2024H2"),
    ("2025-01-01", "2025-07-01", "2025H1"),
    ("2025-07-01", "2026-02-01", "2025H2"),
]


def create_query(name, sql):
    resp = requests.post(
        f"{DUNE_API}/query", headers=HEADERS,
        json={"name": f"sol_exp_{name}", "query_sql": sql.strip(), "is_private": True},
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
        print("    Timed out after max polls")
        return None
    results_resp = requests.get(f"{DUNE_API}/execution/{execution_id}/results",
                                headers=HEADERS, params={"limit": 500000}, timeout=120)
    if results_resp.status_code != 200:
        return None
    rows = results_resp.json().get("result", {}).get("rows", [])
    return pd.DataFrame(rows) if rows else None


def build_single_entity_sql(entity_name, addresses, start, end):
    """Build SQL for a single entity's Solana addresses using WHERE IN, not JOIN."""
    addr_list = ", ".join(f"'{a}'" for a in addresses)
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
AND (from_owner IN ({addr_list}) OR to_owner IN ({addr_list}))
GROUP BY 1, 2, 3
ORDER BY 1
"""


def run_query(name, sql):
    print(f"  [{name}]")
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
        print(f"    OK: {len(df)} rows")
    else:
        print("    No data returned")
    return df


def main():
    print("=" * 60)
    print("SOLANA GATEWAY EXPANSION (individual entity queries)")
    print("=" * 60)

    gateways = get_gateways_by_chain("solana")

    # Group by entity
    entity_addrs = {}
    for g in gateways:
        ent = g["entity"]
        if ent not in entity_addrs:
            entity_addrs[ent] = {"addresses": [], "tier": g["tier"]}
        entity_addrs[ent]["addresses"].append(g["address"])

    print(f"\nEntities: {list(entity_addrs.keys())}")
    results = {}
    all_frames = []

    # Load any previously saved per-entity CSVs
    SKIP_ENTITIES = set()
    for ent in entity_addrs:
        ent_file = DATA_RAW / f"dune_sol_{ent.replace(' ', '_').lower()}.csv"
        if ent_file.exists():
            prev = pd.read_csv(ent_file)
            for col in ["volume_raw", "n_transfers"]:
                if col in prev.columns:
                    prev[col] = pd.to_numeric(prev[col], errors="coerce")
            all_frames.append(prev)
            SKIP_ENTITIES.add(ent)
            print(f"  (cached) {ent}: {len(prev)} rows")

    # Run each entity x half-year combination
    for entity, info in entity_addrs.items():
        if entity in SKIP_ENTITIES:
            continue
        addrs = info["addresses"]
        tier = info["tier"]
        ent_label = entity.replace(" ", "_").lower()
        print(f"\n--- {entity} (Tier {tier}, {len(addrs)} addrs) ---")

        entity_frames = []
        for start, end, period_label in QUARTERS:
            name = f"{ent_label}_{period_label}"
            sql = build_single_entity_sql(entity, addrs, start, end)
            df = run_query(name, sql)
            if df is not None:
                df["tier"] = tier
                entity_frames.append(df)
                results[name] = f"OK ({len(df)} rows)"
            else:
                results[name] = "FAILED"

        if entity_frames:
            combined = pd.concat(entity_frames, ignore_index=True)
            for col in ["volume_raw", "n_transfers"]:
                if col in combined.columns:
                    combined[col] = pd.to_numeric(combined[col], errors="coerce")
            # Save per-entity CSV for resume capability
            ent_path = DATA_RAW / f"dune_sol_{ent_label}.csv"
            combined.to_csv(ent_path, index=False)
            all_frames.append(combined)
            total_vol = combined["volume_raw"].sum() / 1e6 if "volume_raw" in combined.columns else 0
            print(f"  {entity} total: {len(combined)} rows, ${total_vol:,.0f}M")

    # Combine all
    if all_frames:
        full = pd.concat(all_frames, ignore_index=True)
        for col in ["volume_raw", "n_transfers"]:
            if col in full.columns:
                full[col] = pd.to_numeric(full[col], errors="coerce")
        # Normalize volume: raw → USD (divide by 1e6 for 6-decimal tokens)
        if "volume_raw" in full.columns:
            full["volume_usd"] = full["volume_raw"] / 1e6
        path = DATA_RAW / "dune_solana_gateway.csv"
        full.to_csv(path, index=False)
        print(f"\n  Full Solana gateway: {len(full)} rows saved to {path}")
        print(f"  Entities: {full['entity'].nunique()}")
        print(f"  Total volume: ${full['volume_usd'].sum():,.0f}M")
        results["solana_combined"] = f"OK ({len(full)} rows)"
    else:
        results["solana_combined"] = "FAILED"

    print("\n" + "=" * 60)
    print("RESULTS:")
    for name, status in results.items():
        print(f"  {name}: {status}")
    save_json(results, "solana_expansion_status.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
