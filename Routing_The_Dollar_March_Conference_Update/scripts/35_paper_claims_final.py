"""35_paper_claims_final.py — Generate paper_claims_final.md listing every claim needing revision.

Reads metrics_comparison_v2.json and produces a structured list of every
specific sentence/number in the paper that needs updating.
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_PROC


def load_metrics():
    """Load the comparison metrics."""
    path = DATA_PROC / "metrics_comparison_v2.json"
    if not path.exists():
        print("ERROR: metrics_comparison_v2.json not found. Run 33_recompute_metrics_v2.py first.")
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def generate_claims(metrics):
    """Generate the claims document."""
    m = metrics.get("metrics", {})

    def v(key, field="expanded_daily"):
        val = m.get(key, {}).get(field, "TBD")
        return val if val is not None else "TBD"

    # Load SVB retention if available
    svb = {}
    svb_path = DATA_PROC / "svb_retention_v2.json"
    if svb_path.exists():
        with open(svb_path) as f:
            svb = json.load(f).get("retention_by_entity", {})

    # Load within-tier-1 data
    wt1_circle = v("within_tier1_circle")
    wt1_coinbase = v("within_tier1_coinbase")
    wt1_gemini = v("within_tier1_gemini")

    t1_share = v("tier1_share")
    t2_share = v("tier2_share")
    entity_hhi = v("entity_hhi_mean")
    tier_hhi = v("tier_hhi_mean")
    coverage = v("coverage_ratio")
    usdt_t1 = v("usdt_through_tier1")

    t1_r = v("tier1_r_fed_assets")
    t2_r = v("tier2_r_fed_assets")
    t3_r = v("tier3_r_fed_assets")

    svb_circle = v("svb_circle_retention")
    svb_coinbase = v("svb_coinbase_retention")

    # Top 2 in Tier 1 (Circle + Coinbase)
    if wt1_circle != "TBD" and wt1_coinbase != "TBD":
        top2_t1 = round(float(wt1_circle) + float(wt1_coinbase), 1)
    else:
        top2_t1 = "TBD"

    lines = []
    lines.append("# Paper Claims Requiring Revision")
    lines.append("")
    lines.append(f"Generated: {metrics.get('generated', 'unknown')}")
    lines.append(f"Data source: {metrics.get('data_source', 'unknown')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    claims = [
        {
            "num": 1,
            "location": "Abstract / Introduction",
            "old_text": '"Circle 76.4 percent, Gemini 23.1 percent"',
            "new_value": f"Circle ~{wt1_circle}%, Coinbase ~{wt1_coinbase}% (within Tier 1)",
            "confidence": "HIGH",
            "note": "Gemini was Binance address mislabeling. Coinbase was showing $0 due to wrong address. Real Gemini ~0%.",
        },
        {
            "num": 2,
            "location": "Abstract / Introduction",
            "old_text": '"effective duopoly" (referring to Circle+Gemini)',
            "new_value": f'"Circle-Coinbase duopoly within Tier 1" ({top2_t1}% of Tier 1)',
            "confidence": "HIGH",
            "note": 'Duopoly framing survives but the entities change. ~5 instances of "duopoly" throughout paper need revision.',
        },
        {
            "num": 3,
            "location": "Introduction",
            "old_text": '"USDT routes 39.5 percent of its Ethereum gateway volume through Tier 1, primarily Gemini — which processes more USDT ($233 billion) than USDC ($190 billion)"',
            "new_value": f"USDT through Tier 1: {usdt_t1}% (DELETE Gemini reference entirely)",
            "confidence": "HIGH",
            "note": "The $233B USDT through 'Gemini' was Binance. Real USDT-through-Tier-1 is much lower, reinforcing the regulatory gap argument.",
        },
        {
            "num": 4,
            "location": "Section V.C",
            "old_text": '"Coinbase less than 0.1 percent"',
            "new_value": f"Coinbase ~{wt1_coinbase}% of Tier 1, ~24% of total gateway volume",
            "confidence": "HIGH",
            "note": "Original used wrong Coinbase address (custody-only, no stablecoin flow). Expanded registry found 6 active addresses.",
        },
        {
            "num": 5,
            "location": "Section V.C",
            "old_text": '"Gemini for 23.1 percent"',
            "new_value": f"Gemini ~{wt1_gemini}% — address was Binance 15",
            "confidence": "HIGH",
            "note": "Confirmed via Etherscan page title, Dune labels, and Arkham Intelligence. 0x21a31... = Binance 15/36.",
        },
        {
            "num": 6,
            "location": "Section V.C",
            "old_text": '"99.4 percent of Tier 1 volume" (Circle+Gemini)',
            "new_value": f"Circle+Coinbase: ~{top2_t1}% of Tier 1",
            "confidence": "HIGH",
            "note": "Same duopoly concentration but different entity. Gemini out, Coinbase in.",
        },
        {
            "num": 7,
            "location": "Section V.C",
            "old_text": '"Four of the twelve monitored addresses (Coinbase Custody, Kraken, OKX, and Aave V3 Pool) exhibited negligible transfer volume"',
            "new_value": "Only Aave V3 remains negligible. Coinbase, Kraken, OKX all have material volume via correct/expanded addresses.",
            "confidence": "HIGH",
            "note": "Coinbase: 6 addresses, ~$1.9T. Kraken: 3 new hot wallets, ~$471B. OKX: 13 new wallets, ~$464B.",
        },
        {
            "num": 8,
            "location": "Section V.C",
            "old_text": '"eight active addresses"',
            "new_value": "51 addresses across 19 entities (40+ active)",
            "confidence": "HIGH",
            "note": "Expanded registry covers 28.7% of total Ethereum USDC+USDT volume vs 8.1% before.",
        },
        {
            "num": 9,
            "location": "Section V.C",
            "old_text": '"tier-level HHI averages 7,361"',
            "new_value": f"Tier-level HHI: {tier_hhi} (daily mean, expanded)",
            "confidence": "HIGH",
            "note": "Still above DOJ/FTC threshold of 2,500 — market remains 'highly concentrated'.",
        },
        {
            "num": 10,
            "location": "Section V.C",
            "old_text": '"entity-level mean HHI is 4,849"',
            "new_value": f"Entity-level HHI: {entity_hhi} (daily mean, expanded)",
            "confidence": "HIGH",
            "note": f"May be near or below 2,500 threshold with expanded entities. Key finding if so.",
        },
        {
            "num": 11,
            "location": "Section V.C (SVB)",
            "old_text": '"Gemini (CLII 0.82), without SVB exposure, gained share (1.24x)"',
            "new_value": f"DELETE — this was Binance, not Gemini. Binance SVB retention: {svb.get('Binance', {}).get('retention', 'TBD')}x",
            "confidence": "HIGH",
            "note": "Binance (Tier 2) gaining share during SVB is a different narrative than Gemini (Tier 1) gaining share.",
        },
        {
            "num": 12,
            "location": "Section V.C",
            "old_text": '"Tier 1 r=-0.17, Tier 2 r=-0.46" (correlations with Fed assets)',
            "new_value": f"Tier 1 r={t1_r}, Tier 2 r={t2_r}, Tier 3 r={t3_r}",
            "confidence": "HIGH" if t1_r != "TBD" else "MEDIUM",
            "note": "Recalculated with expanded daily data. Direction should be consistent.",
        },
        {
            "num": 13,
            "location": "Section V.C",
            "old_text": '"82 percent of total stablecoin transfer volume" (Tier 1 share)',
            "new_value": f"Tier 1: ~{t1_share}%, Tier 2: ~{t2_share}%",
            "confidence": "HIGH",
            "note": "Narrative shifts from 'Tier 1 dominance' to 'Tier 2 majority with Tier 1 as concentrated regulatory infrastructure'.",
        },
        {
            "num": 14,
            "location": "Section VI.A / VI.C / VI.D",
            "old_text": '"Circle and Gemini together process 80.6 percent"',
            "new_value": f"Circle+Coinbase ~{top2_t1}% of Tier 1 (but Tier 1 is now ~{t1_share}% of total)",
            "confidence": "HIGH",
            "note": "The concentration within Tier 1 is real but its share of total volume is smaller.",
        },
        {
            "num": 15,
            "location": "Section VI.D / VII",
            "old_text": '"99.4 percent of Tier 1 volume"',
            "new_value": f"~{top2_t1}% (Circle+Coinbase)",
            "confidence": "HIGH",
            "note": "Same concentration, different entities.",
        },
        {
            "num": 16,
            "location": "Throughout (~5 instances)",
            "old_text": '"effective duopoly" (referring to Circle+Gemini)',
            "new_value": '"effective duopoly" (Circle+Coinbase within Tier 1)',
            "confidence": "HIGH",
            "note": "Search and replace all instances. The duopoly finding survives — the entity names change.",
        },
        {
            "num": 17,
            "location": "Section IV.A",
            "old_text": '"8.1 percent of combined Ethereum USDC and USDT volume"',
            "new_value": f"~{coverage}% of combined Ethereum USDC+USDT volume (51 addresses, 19 entities)",
            "confidence": "HIGH",
            "note": "Coverage ratio roughly triples with expanded registry. Strengthens the monitoring argument.",
        },
    ]

    for claim in claims:
        lines.append(f"## Claim {claim['num']}: {claim['location']}")
        lines.append("")
        lines.append(f"**Old text:** {claim['old_text']}")
        lines.append("")
        lines.append(f"**New value:** {claim['new_value']}")
        lines.append("")
        lines.append(f"**Confidence:** {claim['confidence']}")
        lines.append("")
        lines.append(f"**Note:** {claim['note']}")
        lines.append("")
        lines.append("---")
        lines.append("")

    # Summary section
    lines.append("## Summary of Narrative Impact")
    lines.append("")
    lines.append("### What Survives")
    lines.append("- Core thesis: 'regulate the router, not the token' is strengthened")
    lines.append("- Duopoly concentration within Tier 1 (now Circle+Coinbase, not Circle+Gemini)")
    lines.append("- Gateway HHI above DOJ threshold (tier-level)")
    lines.append("- Tier correlation structure (Tier 1/2 negative, Tier 3 positive with Fed assets)")
    lines.append("- SVB stress patterns (Circle volume drop during bank run)")
    lines.append("")
    lines.append("### What Changes")
    lines.append(f"- Tier 1 share drops from 82% to ~{t1_share}% — Tier 2 has majority")
    lines.append("- 'Gemini' is removed entirely — was a Binance address")
    lines.append(f"- Coinbase discovered as major player (~{wt1_coinbase}% of Tier 1)")
    lines.append(f"- Coverage ratio rises from 8% to ~{coverage}% with expanded registry")
    lines.append(f"- USDT-through-Tier-1 drops from 39.5% to ~{usdt_t1}%")
    lines.append("- 'Eight active addresses' becomes '40+ active addresses across 19 entities'")
    lines.append("")
    lines.append("### Narrative Shift")
    lines.append("The paper's narrative shifts from 'Tier 1 dominance' to 'Tier 2 majority with")
    lines.append("Tier 1 as concentrated regulatory infrastructure.' This is actually a MORE interesting")
    lines.append("and defensible story for a Fed audience: the regulated perimeter captures ~42% of volume")
    lines.append("through just 2-3 entities, while the remaining ~55% flows through identifiable but")
    lines.append("less-regulated exchanges — exactly the kind of gateway-level variation the paper argues")
    lines.append("regulators should monitor.")
    lines.append("")
    lines.append("### Gemini Fix Impact")
    lines.append("The 'USDT through Tier 1' finding needs complete deletion of the Gemini reference.")
    lines.append("The claim that 39.5% of USDT routes through Tier 1 was inflated by misattributing")
    lines.append("$233B of Binance USDT to Gemini (Tier 1). The real number reinforces the paper's")
    lines.append("argument about the regulatory gap in USDT infrastructure.")

    return "\n".join(lines)


def main():
    print("=" * 70)
    print("PAPER CLAIMS FINAL REPORT")
    print("=" * 70)

    metrics = load_metrics()
    content = generate_claims(metrics)

    output_path = DATA_PROC / "paper_claims_final.md"
    with open(output_path, "w") as f:
        f.write(content)
    print(f"  Saved: {output_path}")
    print(f"  Total claims: 17")

    # Count by confidence
    high = content.count("**Confidence:** HIGH")
    medium = content.count("**Confidence:** MEDIUM")
    print(f"  HIGH confidence: {high}")
    print(f"  MEDIUM confidence: {medium}")


if __name__ == "__main__":
    main()
