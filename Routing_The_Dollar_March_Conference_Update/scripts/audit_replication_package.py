"""Final audit of the replication package: checks file existence, data integrity, and CLII consistency."""
import os
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PASS = 0
FAIL = 0


def check(description, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {description}")
    else:
        FAIL += 1
        print(f"  FAIL  {description}")
    if detail:
        print(f"        {detail}")


def main():
    print("=" * 70)
    print("REPLICATION PACKAGE AUDIT")
    print("=" * 70)

    # --- 1. Required files exist ---
    print("\n[File Existence]")
    required_files = [
        "README.md",
        "requirements.txt",
        ".gitignore",
        "Routing_the_Dollar_March_Conference_Update.docx",
        "Routing_the_Dollar_Supplement_March_Conference_Update.docx",
        "paper_v25.md",
        "config/settings.py",
        "data/raw/NANSEN_NOTICE.md",
        "data/raw/dune_eth_daily_expanded_v2.csv",
        "data/raw/dune_eth_expanded_gateway_v2.csv",
        "data/raw/dune_eth_total_v2.csv",
        "data/raw/fred_all_series.csv",
        "data/processed/unified_extended_dataset.csv",
        "data/processed/clii_nofreeze_robustness.csv",
        "data/processed/vecm_reconciliation.json",
        "data/processed/fomc_events.csv",
        "data/processed/exhibit_C1_gateway_shares_daily_upgraded.csv",
        "data/processed/exhibit_C2_concentration_daily_upgraded.csv",
        "data/processed/gateway_volume_summary_v2.csv",
        "data/processed/placebo_swing_stats.csv",
    ]
    for f in required_files:
        path = ROOT / f
        check(f, path.exists())

    # --- 2. Dune SQL queries ---
    print("\n[Dune SQL Queries]")
    sql_dir = ROOT / "queries" / "dune"
    check("queries/dune/ directory exists", sql_dir.exists())
    if sql_dir.exists():
        sql_files = list(sql_dir.glob("*.sql"))
        check(f"SQL files present (expect 20+)", len(sql_files) >= 20,
              f"got {len(sql_files)} .sql files")
        key_queries = [
            "phase1_eth_expanded_gateway.sql",
            "phase1_eth_total_volume.sql",
            "phase2_tron_gateway.sql",
            "phase3_solana_gateway.sql",
        ]
        for q in key_queries:
            check(f"  {q}", (sql_dir / q).exists())

    # --- 3. Data files are non-empty ---
    print("\n[Data File Sizes]")
    for d in ["data/raw", "data/processed"]:
        dp = ROOT / d
        if dp.exists():
            csvs = list(dp.glob("*.csv"))
            jsons = list(dp.glob("*.json"))
            empty = [f for f in csvs + jsons if f.stat().st_size == 0]
            check(f"{d}: no empty files", len(empty) == 0,
                  f"{len(empty)} empty files" if empty else f"{len(csvs)} CSVs, {len(jsons)} JSONs")

    # --- 4. No API keys in ANY .py file in the repo ---
    print("\n[Security: No API Keys]")
    import re
    all_py = list(ROOT.rglob("*.py"))
    leaked_files = []
    for py_file in all_py:
        try:
            content = py_file.read_text()
            # Match API_KEY = "..." where value is 10+ chars (real key, not empty placeholder)
            real_keys = re.findall(r'API_KEY\s*=\s*"([^"]{10,})"', content)
            if real_keys:
                rel = py_file.relative_to(ROOT)
                leaked_files.append(f"{rel} ({len(real_keys)} key(s))")
        except Exception:
            pass
    check(f"No hardcoded API keys in {len(all_py)} .py files",
          len(leaked_files) == 0,
          "; ".join(leaked_files) if leaked_files else "all clean")

    # --- 4b. Config completeness ---
    print("\n[Config Completeness]")
    config_path = ROOT / "config" / "settings.py"
    if config_path.exists():
        config_content = config_path.read_text()
        check("config/settings.py has GATEWAYS", "GATEWAYS" in config_content)
        check("config/settings.py has FOMC_DATES", "FOMC_DATES" in config_content)
        check("config/settings.py has FRED_SERIES", "FRED_SERIES" in config_content)
    else:
        check("config/settings.py exists", False)

    # --- 5. Exhibit count ---
    print("\n[Exhibits]")
    media_pngs = list((ROOT / "media").glob("*.png")) if (ROOT / "media").exists() else []
    exhibit_pngs = list((ROOT / "data" / "exhibits").glob("*.png")) if (ROOT / "data" / "exhibits").exists() else []
    total_exhibits = len(media_pngs) + len(exhibit_pngs)
    check(f"Exhibits: {total_exhibits} total PNGs", total_exhibits >= 70,
          f"media/: {len(media_pngs)}, data/exhibits/: {len(exhibit_pngs)}")

    # --- 6. CLII scores in processed data match Table 2a ---
    print("\n[CLII Score Consistency]")
    TABLE_2A = {
        'Circle': 0.92, 'Paxos': 0.88, 'PayPal': 0.88,
        'Coinbase': 0.85, 'Gemini': 0.82, 'BitGo': 0.80,
        'Robinhood': 0.75,
        'Kraken': 0.58, 'Tether': 0.45,
        'OKX': 0.40, 'Bybit': 0.40, 'Binance': 0.38,
        'Aave V3': 0.20, 'Curve 3pool': 0.18, '1inch': 0.18,
        'Compound V3': 0.18,
        'Uniswap V3': 0.15, 'Uniswap Universal Router': 0.15,
        'Tornado Cash': 0.02,
    }
    try:
        import pandas as pd
        nf = pd.read_csv(ROOT / "data" / "processed" / "clii_nofreeze_robustness.csv")
        name_col = [c for c in nf.columns if c.lower() in ("entity", "name", "gateway")][0]
        clii_col = [c for c in nf.columns if "baseline" in c.lower()][0]
        mismatches = []
        for _, row in nf.iterrows():
            name = row[name_col]
            score = row[clii_col]
            expected = TABLE_2A.get(name)
            if expected is not None and abs(score - expected) > 0.005:
                mismatches.append(f"{name}: got {score}, expected {expected}")
        check("CLII baseline scores match Table 2a", len(mismatches) == 0,
              "; ".join(mismatches) if mismatches else f"all {len(nf)} entities match")
    except Exception as e:
        check("CLII score check", False, str(e))

    # --- 7. Scripts directory ---
    print("\n[Scripts]")
    scripts = list((ROOT / "scripts").glob("*.py"))
    check(f"Scripts: {len(scripts)} Python files", len(scripts) >= 50,
          f"in scripts/")

    # --- Summary ---
    print("\n" + "=" * 70)
    total = PASS + FAIL
    print(f"AUDIT: {PASS} passed, {FAIL} failed (of {total} checks)")
    if FAIL == 0:
        print("STATUS: REPLICATION PACKAGE IS CLEAN")
    else:
        print("STATUS: ISSUES FOUND — review above")
    print("=" * 70)

    return 1 if FAIL > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
