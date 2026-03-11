"""32_dune_daily_expanded.py — Execute daily expanded gateway query on Dune.

Runs the complete 51-address daily query, plus verification queries.
If the full 3-year query times out, automatically splits into year chunks.
"""
import requests, pandas as pd, time, sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "config"))
from settings import DUNE_API_KEY
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_RAW, DATA_PROC, save_json

DUNE_API = "https://api.dune.com/api/v1"
HEADERS = {"X-Dune-API-Key": DUNE_API_KEY, "Content-Type": "application/json"}
SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def create_query(name, sql):
    """Create a Dune query and return its query_id."""
    resp = requests.post(
        f"{DUNE_API}/query",
        headers=HEADERS,
        json={"name": f"fed_paper_{name}_{int(time.time())}", "query_sql": sql.strip(), "is_private": True},
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"    Create failed: {resp.status_code} {resp.text[:300]}")
        return None
    query_id = resp.json().get("query_id")
    print(f"    Created query ID: {query_id}")
    return query_id


def execute_query(query_id, performance="medium"):
    """Execute a Dune query by ID and return execution_id."""
    resp = requests.post(
        f"{DUNE_API}/query/{query_id}/execute",
        headers=HEADERS,
        json={"performance": performance},
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"    Execute failed: {resp.status_code} {resp.text[:300]}")
        return None
    execution_id = resp.json().get("execution_id")
    print(f"    Execution ID: {execution_id}")
    return execution_id


def poll_and_fetch(execution_id, max_polls=180, poll_interval=10):
    """Poll for completion and fetch results. Returns DataFrame or None."""
    for attempt in range(max_polls):
        time.sleep(poll_interval)
        try:
            status_resp = requests.get(
                f"{DUNE_API}/execution/{execution_id}/status",
                headers=HEADERS,
                timeout=30,
            )
            if status_resp.status_code != 200:
                continue
            state = status_resp.json().get("state", "")
            if attempt % 6 == 0:
                print(f"    Poll {attempt + 1}/{max_polls}: {state}")

            if state == "QUERY_STATE_COMPLETED":
                break
            elif state in ("QUERY_STATE_FAILED", "QUERY_STATE_CANCELLED"):
                error = status_resp.json().get("error", "unknown")
                print(f"    Query failed: {error}")
                return None
        except Exception as e:
            print(f"    Poll error: {e}")
    else:
        print("    Timed out waiting for query")
        return None

    # Fetch all results with pagination
    all_rows = []
    offset = 0
    limit = 250000
    while True:
        results_resp = requests.get(
            f"{DUNE_API}/execution/{execution_id}/results",
            headers=HEADERS,
            params={"limit": limit, "offset": offset},
            timeout=120,
        )
        if results_resp.status_code != 200:
            print(f"    Results failed: {results_resp.status_code}")
            break
        rows = results_resp.json().get("result", {}).get("rows", [])
        if not rows:
            break
        all_rows.extend(rows)
        print(f"    Fetched {len(all_rows)} rows so far...")
        if len(rows) < limit:
            break
        offset += limit
        time.sleep(1)

    if not all_rows:
        print("    No rows returned")
        return None

    return pd.DataFrame(all_rows)


def run_query(name, sql, performance="medium"):
    """Full pipeline: create -> execute -> poll -> fetch. Returns DataFrame."""
    print(f"\n  [{name}]")
    query_id = create_query(name, sql)
    if not query_id:
        return None
    execution_id = execute_query(query_id, performance)
    if not execution_id:
        return None
    return poll_and_fetch(execution_id)


def run_daily_expanded():
    """Run the main daily expanded gateway query."""
    print("=" * 70)
    print("TASK 1: Daily Expanded Gateway Query (51 addresses)")
    print("=" * 70)

    sql = (SQL_DIR / "exhibit_A_daily_v2.sql").read_text()

    # Try full 3-year query first
    print("\nAttempting full 3-year query...")
    df = run_query("daily_expanded_v2_full", sql, performance="medium")

    if df is not None:
        print(f"  Full query succeeded: {len(df)} rows")
        df.to_csv(DATA_RAW / "dune_eth_daily_expanded_v2.csv", index=False)
        print(f"  Saved: {DATA_RAW / 'dune_eth_daily_expanded_v2.csv'}")
        return df

    # If full query failed, split by year
    print("\n  Full query failed. Splitting by year...")
    year_ranges = [
        ("2023-02-01", "2024-02-01", "yr1"),
        ("2024-02-01", "2025-02-01", "yr2"),
        ("2025-02-01", "2026-02-01", "yr3"),
    ]
    frames = []
    for start, end, label in year_ranges:
        year_sql = sql.replace(
            "AND e.evt_block_time >= TIMESTAMP '2023-02-01'\nAND e.evt_block_time < TIMESTAMP '2026-02-01'",
            f"AND e.evt_block_time >= TIMESTAMP '{start}'\nAND e.evt_block_time < TIMESTAMP '{end}'"
        )
        df_yr = run_query(f"daily_expanded_v2_{label}", year_sql, performance="medium")
        if df_yr is not None:
            frames.append(df_yr)
            print(f"    {label}: {len(df_yr)} rows")
        else:
            print(f"    {label}: FAILED")
        time.sleep(2)

    if frames:
        combined = pd.concat(frames, ignore_index=True)
        combined.to_csv(DATA_RAW / "dune_eth_daily_expanded_v2.csv", index=False)
        print(f"  Combined: {len(combined)} rows")
        print(f"  Saved: {DATA_RAW / 'dune_eth_daily_expanded_v2.csv'}")
        return combined

    print("  ALL YEAR QUERIES FAILED")
    return None


def run_verification_queries():
    """Run address verification queries (Tasks 2a, 2b, 2c)."""
    print("\n" + "=" * 70)
    print("TASK 2: Address Verification Queries")
    print("=" * 70)

    results = {}

    # 2a: Gemini verification
    print("\n--- 2a: Gemini Address Verification ---")
    sql = (SQL_DIR / "gemini_verification.sql").read_text()
    df = run_query("gemini_verify", sql, performance="medium")
    if df is not None:
        gemini_data = {}
        for _, row in df.iterrows():
            label = row.get("label", "unknown")
            gemini_data[label] = {
                "total_volume_usd": round(float(row.get("total_volume_usd", 0)), 2),
                "n_transfers": int(row.get("n_transfers", 0)),
            }
        results["gemini_verification"] = gemini_data
        print(f"    Results: {json.dumps(gemini_data, indent=2)}")
    else:
        results["gemini_verification"] = "QUERY_FAILED"

    # 2b: Paxos verification
    print("\n--- 2b: Paxos Address Verification ---")
    sql = (SQL_DIR / "paxos_verification.sql").read_text()
    df = run_query("paxos_verify", sql, performance="medium")
    if df is not None and len(df) > 0:
        results["paxos_verification"] = df.to_dict(orient="records")
        print(f"    Labels found: {df.to_dict(orient='records')}")
    else:
        results["paxos_verification"] = "no_labels_found_or_query_failed"
        print("    No labels found (address may be unlabeled on Dune)")

    # 2c: Gemini cold wallet
    print("\n--- 2c: Gemini Cold Wallet Stablecoin Activity ---")
    sql = (SQL_DIR / "gemini_cold_wallet.sql").read_text()
    df = run_query("gemini_cold", sql, performance="medium")
    if df is not None and len(df) > 0:
        cold_data = {}
        for _, row in df.iterrows():
            token = row.get("token", "unknown")
            cold_data[token] = {
                "total_volume_usd": round(float(row.get("total_volume_usd", 0)), 2),
                "n_transfers": int(row.get("n_transfers", 0)),
            }
        results["gemini_cold_wallet"] = cold_data
        total_vol = sum(v["total_volume_usd"] for v in cold_data.values())
        results["gemini_cold_wallet_material"] = total_vol > 100_000_000
        print(f"    Total volume: ${total_vol:,.0f}")
        print(f"    Material (>$100M): {results['gemini_cold_wallet_material']}")
    else:
        results["gemini_cold_wallet"] = "no_activity_or_query_failed"
        results["gemini_cold_wallet_material"] = False
        print("    No stablecoin activity found")

    save_json(results, "gemini_verification.json")
    return results


def main():
    if not DUNE_API_KEY:
        print("ERROR: Set DUNE_API_KEY in config/settings.py")
        sys.exit(1)

    print("=" * 70)
    print("DUNE DAILY EXPANDED GATEWAY RE-QUERY")
    print("51 addresses | 19 entities | Daily granularity | 2023-02 to 2026-02")
    print("=" * 70)

    # Run verification queries first (fast)
    verify_results = run_verification_queries()

    # Run the main daily query (slow)
    daily_df = run_daily_expanded()

    if daily_df is not None:
        # Quick validation
        print("\n" + "=" * 70)
        print("VALIDATION")
        print("=" * 70)
        print(f"  Total rows: {len(daily_df)}")
        print(f"  Entities: {daily_df['entity'].nunique()}")
        print(f"  Date range: {daily_df['day'].min()} to {daily_df['day'].max()}")
        print(f"  Total volume: ${daily_df['volume_usd'].sum() / 1e12:.2f}T")

        by_entity = daily_df.groupby("entity")["volume_usd"].sum().sort_values(ascending=False)
        print(f"\n  Top entities:")
        for entity, vol in by_entity.head(10).items():
            print(f"    {entity}: ${vol / 1e9:,.1f}B")

        by_tier = daily_df.groupby("tier")["volume_usd"].sum()
        total = by_tier.sum()
        for tier, vol in sorted(by_tier.items()):
            print(f"    Tier {tier}: ${vol / 1e9:,.1f}B ({vol / total * 100:.1f}%)")
    else:
        print("\n  WARNING: Daily query failed. Metrics computation will use monthly data.")

    print("\n" + "=" * 70)
    print("DONE — Run 33_recompute_metrics_v2.py next")
    print("=" * 70)


if __name__ == "__main__":
    main()
