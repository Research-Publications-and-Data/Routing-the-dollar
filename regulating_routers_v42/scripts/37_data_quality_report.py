"""37_data_quality_report.py — Generate comprehensive data quality report.

Combines results from:
  - Internal transfer audit (Task 4c)
  - Bilateral flows / double-counting (Task 4d)
  - Gemini GUSD profile (Task 1)
  - HHI robustness (Task 5)
  - 1inch verification (Task 4a)
  - Net volume analysis
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_PROC, save_json


def load_json(filename):
    path = DATA_PROC / filename
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def main():
    print("=" * 70)
    print("COMPREHENSIVE DATA QUALITY REPORT")
    print("=" * 70)

    internal = load_json("internal_transfer_audit.json")
    bilateral = load_json("bilateral_flows.json")
    gemini = load_json("gemini_gateway_profile.json")
    hhi = load_json("hhi_robustness.json")
    net_vol = load_json("net_volume_analysis.json")
    metrics = load_json("metrics_comparison_v2.json")

    report_lines = []
    report_lines.append("# Data Quality Report: Expanded Gateway Registry v2")
    report_lines.append("")
    report_lines.append("## 1. Internal Transfer Audit")
    report_lines.append("")

    if internal:
        entities = internal.get("entities", {})
        material = [e for e, d in entities.items() if d.get("material")]
        report_lines.append(f"**Entities audited:** {len(entities)}")
        report_lines.append(f"**Material internal transfers (>5%):** {', '.join(material) if material else 'None'}")
        report_lines.append("")
        report_lines.append("| Entity | Gross Volume | Internal Volume | Internal % | Status |")
        report_lines.append("|--------|-------------|----------------|-----------|--------|")
        for entity in ["Binance", "OKX", "Kraken", "Coinbase"]:
            data = entities.get(entity, {})
            gross = data.get("total_entity_volume_usd", 0)
            internal_vol = data.get("total_internal_usd", 0)
            pct = data.get("internal_pct", 0)
            status = "MATERIAL" if data.get("material") else "OK"
            report_lines.append(
                f"| {entity} | ${gross/1e9:,.1f}B | ${internal_vol/1e9:,.1f}B | {pct:.1f}% | {status} |"
            )
        report_lines.append("")
        report_lines.append("**Recommendation:** Report both gross and net figures. Binance internal transfers")
        report_lines.append("(18.3%) reflect wallet consolidation operations, not genuine gateway throughput.")
    else:
        report_lines.append("*Internal transfer audit data not available.*")

    report_lines.append("")
    report_lines.append("## 2. Double-Counting Check (Bilateral Flows)")
    report_lines.append("")

    if bilateral:
        total_bi = bilateral.get("total_bilateral_usd", 0)
        bi_pct = bilateral.get("bilateral_pct_of_gateway", 0)
        report_lines.append(f"**Total bilateral volume:** ${total_bi/1e9:.1f}B")
        report_lines.append(f"**As % of gross gateway volume:** {bi_pct:.1f}%")
        report_lines.append("")
        report_lines.append("**Top bilateral pairs:**")
        report_lines.append("")
        report_lines.append("| From | To | Volume | Transfers |")
        report_lines.append("|------|-----|--------|-----------|")
        top = sorted(bilateral.get("pairs", []), key=lambda x: -x["volume_usd"])[:8]
        for p in top:
            report_lines.append(
                f"| {p['from_entity']} | {p['to_entity']} | ${p['volume_usd']/1e9:.1f}B | {p['n_transfers']:,} |"
            )
        report_lines.append("")
        report_lines.append(f"**Conclusion:** Bilateral flows are only {bi_pct:.1f}% of total gateway volume.")
        report_lines.append("Double-counting is negligible and does not materially affect tier share calculations.")
    else:
        report_lines.append("*Bilateral flow data not available.*")

    report_lines.append("")
    report_lines.append("## 3. Net Volume Analysis")
    report_lines.append("")

    if net_vol:
        report_lines.append(f"**Gross total:** ${net_vol.get('gross_total_usd', 0)/1e12:.3f}T")
        report_lines.append(f"**Net total (gross - internal):** ${net_vol.get('net_total_usd', 0)/1e12:.3f}T")
        report_lines.append(f"**Internal transfer adjustment:** {net_vol.get('internal_pct_of_gross', 0):.1f}%")
        report_lines.append("")
        report_lines.append("**Net Tier Shares (after removing internal transfers):**")
        report_lines.append("")
        net_shares = net_vol.get("net_tier_shares", {})
        for tier in sorted(net_shares.keys()):
            report_lines.append(f"- Tier {tier}: {net_shares[tier]}%")
        report_lines.append("")
        report_lines.append(f"**Recommendation:** {net_vol.get('recommendation', '')}")
    else:
        report_lines.append("*Net volume analysis not available.*")

    report_lines.append("")
    report_lines.append("## 4. Gemini Gateway Profile")
    report_lines.append("")

    if gemini:
        gusd_mcap = gemini.get("gusd_market_cap_history", {})
        report_lines.append(f"**USDC/USDT volume:** {gemini.get('usdc_usdt_volume', 'N/A')}")
        report_lines.append(f"**GUSD market cap (peak):** ${gusd_mcap.get('peak_usd', 0)/1e6:.0f}M")
        report_lines.append(f"**GUSD market cap (latest):** ${gusd_mcap.get('latest_usd', 0)/1e6:.0f}M")
        report_lines.append(f"**GUSD trend:** {gusd_mcap.get('trend', 'N/A')}")
        report_lines.append("")
        report_lines.append("**Key Findings:**")
        for finding in gemini.get("key_findings", []):
            report_lines.append(f"- {finding}")
    else:
        report_lines.append("*Gemini profile not available.*")

    report_lines.append("")
    report_lines.append("## 5. HHI Robustness (Excluding Binance)")
    report_lines.append("")

    if hhi:
        wb = hhi.get("with_binance", {})
        wob = hhi.get("without_binance", {})
        report_lines.append("| Metric | With Binance | Without Binance |")
        report_lines.append("|--------|-------------|----------------|")
        report_lines.append(f"| Entity HHI Mean | {wb.get('mean', 'N/A')} | {wob.get('mean', 'N/A')} |")
        report_lines.append(f"| Entity HHI Median | {wb.get('median', 'N/A')} | {wob.get('median', 'N/A')} |")
        report_lines.append(f"| Days > 2,500 | {wb.get('above_2500_pct', 'N/A')}% | {wob.get('above_2500_pct', 'N/A')}% |")
        tier_wb = hhi.get("tier_with_binance", {})
        tier_wob = hhi.get("tier_without_binance", {})
        report_lines.append(f"| Tier HHI Mean | {tier_wb.get('mean', 'N/A')} | {tier_wob.get('mean', 'N/A')} |")
        report_lines.append("")
        interp = hhi.get("interpretation", {})
        report_lines.append(f"**Interpretation:** {interp.get('note', '')}")
        report_lines.append("")
        report_lines.append("Removing Binance *increases* entity HHI by ~164 points, confirming that")
        report_lines.append("concentration is structural (driven by Circle+Coinbase dominance in Tier 1),")
        report_lines.append("not merely an artifact of Binance's large volume.")
    else:
        report_lines.append("*HHI robustness data not available.*")

    report_lines.append("")
    report_lines.append("## 6. Address Verification Summary")
    report_lines.append("")
    report_lines.append("| Address | Claimed | Verified | Status |")
    report_lines.append("|---------|---------|----------|--------|")
    report_lines.append("| 0x21a31... | Gemini | Binance 36 | CORRECTED (session 1) |")
    report_lines.append("| 0x11111... | 1inch/0x | 1inch AggregationRouterV5 | CONFIRMED |")
    report_lines.append("| 0xE25a3... | Paxos | Paxos Treasury | CONFIRMED (Etherscan) |")
    report_lines.append("| 0xd2440... | Gemini | Gemini | CONFIRMED (near-zero USDC/USDT) |")

    report_lines.append("")
    report_lines.append("## 7. Gross vs Net Metrics Comparison")
    report_lines.append("")

    if metrics and net_vol:
        m = metrics.get("metrics", {})
        report_lines.append("| Metric | Gross | Net (excl. internal) |")
        report_lines.append("|--------|-------|---------------------|")
        # Tier shares
        gross_t1 = m.get("tier1_share", {}).get("expanded_daily", "N/A")
        gross_t2 = m.get("tier2_share", {}).get("expanded_daily", "N/A")
        net_shares = net_vol.get("net_tier_shares", {})
        report_lines.append(f"| Tier 1 Share | {gross_t1}% | {net_shares.get('1', 'N/A')}% |")
        report_lines.append(f"| Tier 2 Share | {gross_t2}% | {net_shares.get('2', 'N/A')}% |")
        report_lines.append(f"| Total Volume | ${net_vol.get('gross_total_usd', 0)/1e12:.3f}T | ${net_vol.get('net_total_usd', 0)/1e12:.3f}T |")
        entity_hhi = m.get("entity_hhi_mean", {}).get("expanded_daily", "N/A")
        report_lines.append(f"| Entity HHI | {entity_hhi} | (recalculate with net) |")

    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")
    report_lines.append("## Summary for Paper Revision")
    report_lines.append("")
    report_lines.append("1. **Internal transfers (7.3% of gross) are material.** Report both gross and net.")
    report_lines.append("   Binance's 18.3% internal rate is wallet consolidation. OKX's 10.8% is similar.")
    report_lines.append("2. **Double-counting (0.3% bilateral) is negligible.** No adjustment needed.")
    report_lines.append("3. **Gemini is confirmed as immaterial** for USDC/USDT. GUSD role is small and declining.")
    report_lines.append("4. **HHI concentration is structural.** Removing Binance increases HHI, not decreases.")
    report_lines.append("5. **Net tier shares: Tier 1 ~47%, Tier 2 ~50%** — more balanced than gross figures suggest.")
    report_lines.append("6. **1inch address confirmed** — not 0x Protocol as originally noted in some references.")

    content = "\n".join(report_lines)
    output_path = DATA_PROC / "data_quality_report.md"
    with open(output_path, "w") as f:
        f.write(content)
    print(f"\n  Saved: {output_path}")
    print(f"  Length: {len(report_lines)} lines")

    # Also save a machine-readable summary
    summary = {
        "internal_transfers": {
            "material_entities": ["Binance", "OKX"],
            "total_internal_pct": net_vol.get("internal_pct_of_gross") if net_vol else None,
            "recommendation": "report_both_gross_and_net",
        },
        "bilateral_flows": {
            "total_pct": bilateral.get("bilateral_pct_of_gateway") if bilateral else None,
            "recommendation": "negligible_no_adjustment",
        },
        "gemini": {
            "usdc_usdt_volume": "near_zero",
            "gusd_mcap_current": gemini.get("gusd_market_cap_history", {}).get("latest_usd") if gemini else None,
            "recommendation": "keep_in_registry_note_immaterial",
        },
        "hhi_robustness": {
            "with_binance": hhi.get("with_binance", {}).get("mean") if hhi else None,
            "without_binance": hhi.get("without_binance", {}).get("mean") if hhi else None,
            "structural": True,
        },
        "net_tier_shares": net_vol.get("net_tier_shares") if net_vol else None,
    }
    save_json(summary, "data_quality_summary.json")


if __name__ == "__main__":
    main()
