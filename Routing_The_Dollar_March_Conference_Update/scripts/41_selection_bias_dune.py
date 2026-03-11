"""v26 Selection Bias: Dune queries for empirical grounding.

Queries:
  SB-2: Transfer size distribution (labeled vs unlabeled) — minimum viable
  SB-1a: Top 500 unlabeled addresses with counterparty degree
  SB-1b: Same metrics for 51 labeled gateway addresses

Uses the Dune API v1 create-then-execute pattern (same as 08a).
"""
import os, requests, pandas as pd, time, sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / 'data' / 'raw'
DATA_PROC = ROOT / 'data' / 'processed'

# Dune API key — set via environment variable or config/settings.py
DUNE_API_KEY = os.environ.get("DUNE_API_KEY", "")
DUNE_API = "https://api.dune.com/api/v1"
HEADERS = {"X-Dune-API-Key": DUNE_API_KEY, "Content-Type": "application/json"}

# ── Build 51-address registry CTE from CSV ──────────────────
def load_registry():
    """Load gateway_registry_expanded.csv and return formatted SQL address list."""
    reg = pd.read_csv(DATA_PROC / 'gateway_registry_expanded.csv')
    addrs = reg['address'].str.lower().tolist()
    return addrs

def build_address_values_cte(addrs):
    """Build a VALUES CTE for DuneSQL from address list."""
    lines = []
    for a in addrs:
        lines.append(f"        ({a})")
    return ",\n".join(lines)

def build_address_in_list(addrs):
    """Build an IN (...) clause for DuneSQL."""
    return ", ".join(addrs)


# ── SQL Queries ──────────────────────────────────────────────

def get_sb2_sql(addrs):
    """SB-2: Transfer size distribution, labeled vs unlabeled.
    Uses 6-month window (2024-07-01 to 2025-01-01) for efficiency."""
    addr_list = build_address_in_list(addrs)
    return f"""
WITH labeled_addrs AS (
    SELECT address FROM (VALUES
{build_address_values_cte(addrs)}
    ) AS t(address)
)
SELECT
    CASE
        WHEN t."from" IN (SELECT address FROM labeled_addrs)
          OR t."to" IN (SELECT address FROM labeled_addrs)
        THEN 'labeled' ELSE 'unlabeled'
    END AS address_category,
    CASE
        WHEN CAST(t.value AS DOUBLE) / 1e6 < 100 THEN '1_lt_100'
        WHEN CAST(t.value AS DOUBLE) / 1e6 < 1000 THEN '2_100_1k'
        WHEN CAST(t.value AS DOUBLE) / 1e6 < 10000 THEN '3_1k_10k'
        WHEN CAST(t.value AS DOUBLE) / 1e6 < 100000 THEN '4_10k_100k'
        WHEN CAST(t.value AS DOUBLE) / 1e6 < 1000000 THEN '5_100k_1m'
        WHEN CAST(t.value AS DOUBLE) / 1e6 < 10000000 THEN '6_1m_10m'
        ELSE '7_10m_plus'
    END AS size_bucket,
    COUNT(*) AS n_transfers,
    SUM(CAST(t.value AS DOUBLE) / 1e6) AS total_volume_usd
FROM erc20_ethereum.evt_Transfer t
WHERE t.contract_address IN (
    0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48,
    0xdAC17F958D2ee523a2206206994597C13D831ec7
)
AND t.evt_block_time >= TIMESTAMP '2024-07-01'
AND t.evt_block_time < TIMESTAMP '2025-01-01'
GROUP BY 1, 2
ORDER BY 1, 2
"""


def get_sb1a_sql(addrs):
    """SB-1a: Top 500 unlabeled addresses by volume, with counterparty degree.
    Uses 6-month window for efficiency."""
    addr_list = build_address_in_list(addrs)
    return f"""
WITH labeled_addrs AS (
    SELECT address FROM (VALUES
{build_address_values_cte(addrs)}
    ) AS t(address)
),
outflows AS (
    SELECT
        t."from" AS addr,
        t."to" AS counterparty,
        CAST(t.value AS DOUBLE) / 1e6 AS vol
    FROM erc20_ethereum.evt_Transfer t
    WHERE t.contract_address IN (
        0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48,
        0xdAC17F958D2ee523a2206206994597C13D831ec7
    )
    AND t.evt_block_time >= TIMESTAMP '2024-07-01'
    AND t.evt_block_time < TIMESTAMP '2025-01-01'
),
inflows AS (
    SELECT
        t."to" AS addr,
        t."from" AS counterparty,
        CAST(t.value AS DOUBLE) / 1e6 AS vol
    FROM erc20_ethereum.evt_Transfer t
    WHERE t.contract_address IN (
        0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48,
        0xdAC17F958D2ee523a2206206994597C13D831ec7
    )
    AND t.evt_block_time >= TIMESTAMP '2024-07-01'
    AND t.evt_block_time < TIMESTAMP '2025-01-01'
),
out_agg AS (
    SELECT addr, SUM(vol) AS out_vol, COUNT(*) AS out_n,
           COUNT(DISTINCT counterparty) AS out_degree
    FROM outflows
    WHERE addr != 0x0000000000000000000000000000000000000000
    GROUP BY 1
),
in_agg AS (
    SELECT addr, SUM(vol) AS in_vol, COUNT(*) AS in_n,
           COUNT(DISTINCT counterparty) AS in_degree
    FROM inflows
    WHERE addr != 0x0000000000000000000000000000000000000000
    GROUP BY 1
)
SELECT
    COALESCE(o.addr, i.addr) AS address,
    COALESCE(o.out_vol, 0) + COALESCE(i.in_vol, 0) AS total_volume_usd,
    COALESCE(o.out_n, 0) + COALESCE(i.in_n, 0) AS n_transfers,
    COALESCE(o.out_vol, 0) AS outflow_usd,
    COALESCE(i.in_vol, 0) AS inflow_usd,
    COALESCE(o.out_degree, 0) AS out_degree,
    COALESCE(i.in_degree, 0) AS in_degree,
    CASE WHEN COALESCE(o.out_vol, 0) + COALESCE(i.in_vol, 0) > 0
         THEN LEAST(COALESCE(o.out_vol, 0), COALESCE(i.in_vol, 0))
              / GREATEST(COALESCE(o.out_vol, 0), COALESCE(i.in_vol, 0))
         ELSE 0 END AS flow_symmetry
FROM out_agg o
FULL OUTER JOIN in_agg i ON o.addr = i.addr
WHERE COALESCE(o.addr, i.addr) NOT IN (SELECT address FROM labeled_addrs)
ORDER BY 2 DESC
LIMIT 500
"""


def get_sb1b_sql(addrs):
    """SB-1b: Same metrics for 51 labeled gateway addresses."""
    return f"""
WITH labeled_addrs AS (
    SELECT address FROM (VALUES
{build_address_values_cte(addrs)}
    ) AS t(address)
),
outflows AS (
    SELECT
        t."from" AS addr,
        t."to" AS counterparty,
        CAST(t.value AS DOUBLE) / 1e6 AS vol
    FROM erc20_ethereum.evt_Transfer t
    WHERE t.contract_address IN (
        0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48,
        0xdAC17F958D2ee523a2206206994597C13D831ec7
    )
    AND t.evt_block_time >= TIMESTAMP '2024-07-01'
    AND t.evt_block_time < TIMESTAMP '2025-01-01'
),
inflows AS (
    SELECT
        t."to" AS addr,
        t."from" AS counterparty,
        CAST(t.value AS DOUBLE) / 1e6 AS vol
    FROM erc20_ethereum.evt_Transfer t
    WHERE t.contract_address IN (
        0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48,
        0xdAC17F958D2ee523a2206206994597C13D831ec7
    )
    AND t.evt_block_time >= TIMESTAMP '2024-07-01'
    AND t.evt_block_time < TIMESTAMP '2025-01-01'
),
out_agg AS (
    SELECT addr, SUM(vol) AS out_vol, COUNT(*) AS out_n,
           COUNT(DISTINCT counterparty) AS out_degree
    FROM outflows
    WHERE addr != 0x0000000000000000000000000000000000000000
    GROUP BY 1
),
in_agg AS (
    SELECT addr, SUM(vol) AS in_vol, COUNT(*) AS in_n,
           COUNT(DISTINCT counterparty) AS in_degree
    FROM inflows
    WHERE addr != 0x0000000000000000000000000000000000000000
    GROUP BY 1
)
SELECT
    COALESCE(o.addr, i.addr) AS address,
    COALESCE(o.out_vol, 0) + COALESCE(i.in_vol, 0) AS total_volume_usd,
    COALESCE(o.out_n, 0) + COALESCE(i.in_n, 0) AS n_transfers,
    COALESCE(o.out_vol, 0) AS outflow_usd,
    COALESCE(i.in_vol, 0) AS inflow_usd,
    COALESCE(o.out_degree, 0) AS out_degree,
    COALESCE(i.in_degree, 0) AS in_degree,
    CASE WHEN COALESCE(o.out_vol, 0) + COALESCE(i.in_vol, 0) > 0
         THEN LEAST(COALESCE(o.out_vol, 0), COALESCE(i.in_vol, 0))
              / GREATEST(COALESCE(o.out_vol, 0), COALESCE(i.in_vol, 0))
         ELSE 0 END AS flow_symmetry
FROM out_agg o
FULL OUTER JOIN in_agg i ON o.addr = i.addr
WHERE COALESCE(o.addr, i.addr) IN (SELECT address FROM labeled_addrs)
ORDER BY 2 DESC
"""


# ── Dune API helpers (same pattern as 08a) ───────────────────

def create_query(name, sql):
    resp = requests.post(
        f"{DUNE_API}/query",
        headers=HEADERS,
        json={"name": f"v26_sb_{name}", "query_sql": sql.strip(), "is_private": True},
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"    Create failed: {resp.status_code} {resp.text[:300]}")
        return None
    query_id = resp.json().get("query_id")
    print(f"    Created query ID: {query_id}")
    return query_id


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
    execution_id = resp.json().get("execution_id")
    print(f"    Execution ID: {execution_id}")
    return execution_id


def poll_and_fetch(execution_id, output_file, max_polls=120):
    for attempt in range(max_polls):
        time.sleep(10)
        try:
            status_resp = requests.get(
                f"{DUNE_API}/execution/{execution_id}/status",
                headers=HEADERS, timeout=30,
            )
            if status_resp.status_code != 200:
                continue
            state = status_resp.json().get("state", "")
            if attempt % 3 == 0:
                print(f"    Poll {attempt + 1}: {state}")
            if state == "QUERY_STATE_COMPLETED":
                break
            elif state in ("QUERY_STATE_FAILED", "QUERY_STATE_CANCELLED"):
                error = status_resp.json().get("error", "unknown")
                print(f"    Query failed: {error}")
                return False
        except Exception as e:
            print(f"    Poll error: {e}")
    else:
        print("    Timed out")
        return False

    results_resp = requests.get(
        f"{DUNE_API}/execution/{execution_id}/results",
        headers=HEADERS, params={"limit": 500000}, timeout=120,
    )
    if results_resp.status_code != 200:
        print(f"    Results failed: {results_resp.status_code}")
        return False
    rows = results_resp.json().get("result", {}).get("rows", [])
    if not rows:
        print("    No rows returned")
        return False
    df = pd.DataFrame(rows)
    path = DATA_RAW / output_file
    df.to_csv(path, index=False)
    print(f"    Saved {len(df)} rows to {path}")
    return True


def run_query(name, sql, output_file):
    print(f"\n  [{name}]")
    query_id = create_query(name, sql)
    if not query_id:
        return False
    execution_id = execute_query(query_id)
    if not execution_id:
        return False
    return poll_and_fetch(execution_id, output_file)


# ── Main ─────────────────────────────────────────────────────

def main():
    if not DUNE_API_KEY:
        print("ERROR: No DUNE_API_KEY")
        sys.exit(1)

    print("=" * 60)
    print("v26 SELECTION BIAS: DUNE QUERIES")
    print("=" * 60)
    print("Sample window: 2024-07-01 to 2025-01-01 (6 months)")

    addrs = load_registry()
    print(f"Loaded {len(addrs)} labeled gateway addresses")

    queries = {
        "sb2_size_distribution": {
            "desc": "SB-2: Transfer size distribution (labeled vs unlabeled)",
            "sql": get_sb2_sql(addrs),
            "output": "dune_transfer_size_distribution.csv",
        },
        "sb1a_unlabeled_top500": {
            "desc": "SB-1a: Top 500 unlabeled addresses with degree metrics",
            "sql": get_sb1a_sql(addrs),
            "output": "dune_unlabeled_top500_degree.csv",
        },
        "sb1b_labeled_gateways": {
            "desc": "SB-1b: Labeled gateway degree metrics",
            "sql": get_sb1b_sql(addrs),
            "output": "dune_labeled_gateway_degree.csv",
        },
    }

    # Priority: SB-2 first (minimum viable), then SB-1a/SB-1b
    results = {}
    for name, cfg in queries.items():
        print(f"\n{'=' * 60}")
        print(f"  {cfg['desc']}")
        try:
            ok = run_query(name, cfg["sql"], cfg["output"])
            results[name] = "OK" if ok else "FAILED"
        except Exception as e:
            print(f"    ERROR: {e}")
            results[name] = f"ERROR: {e}"

    print(f"\n{'=' * 60}")
    print("RESULTS:")
    for name, status in results.items():
        print(f"  {name}: {status}")

    # Quick summary of SB-2 if available
    sb2_path = DATA_RAW / "dune_transfer_size_distribution.csv"
    if sb2_path.exists():
        print("\n--- SB-2 Summary ---")
        df = pd.read_csv(sb2_path)
        for cat in df['address_category'].unique():
            sub = df[df['address_category'] == cat]
            vol = sub['total_volume_usd'].sum()
            n = sub['n_transfers'].sum()
            print(f"  {cat}: ${vol/1e12:.2f}T volume, {n/1e6:.1f}M transfers")


if __name__ == "__main__":
    main()
