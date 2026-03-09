"""Task 2: Exhibit 22 — Tron vs. Ethereum Control Layer Comparison.

Side-by-side comparison panel showing structural differences between Ethereum
and Tron's control layers. Reads from tron_identification_v3.csv + tron_final_summary_v3.json,
with Ethereum stats hardcoded from paper.
"""
import pandas as pd, numpy as np, matplotlib.pyplot as plt, matplotlib.patches as mpatches
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_PROC, save_exhibit, setup_plot_style, color


def load_tron_data():
    """Load Tron identification data (v3)."""
    summary = json.load(open(DATA_PROC / "tron_final_summary_v3.json"))
    tron_csv = pd.read_csv(DATA_PROC / "tron_identification_v3.csv")
    return summary, tron_csv


def load_eth_data_driven():
    """Load Ethereum tier shares and HHI from expanded registry v2 data files."""
    # Expanded registry: 19 entities, 51 addresses, 6 Tier 1
    eth = {
        "tier1_pct": 40.8, "tier2_pct": 55.1, "tier3_pct": 4.1,
        "label_rate": 98.0, "hhi": 5021, "n_gateways": 19, "n_tier1": 6,
        "tier1_entities": ["Circle", "Coinbase", "Paxos", "Gemini", "PayPal", "BitGo"],
        "tier2_entities": ["Binance", "Kraken", "OKX", "Bybit", "Tether", "Robinhood"],
        "tier3_entities": ["Uniswap V3", "Uniswap Universal Router", "Curve 3pool",
                           "Aave V3", "1inch", "Compound V3", "Tornado Cash"],
    }
    # Try to load from expanded v2 data files
    try:
        shares = pd.read_csv(DATA_PROC / "exhibit_C1_gateway_shares_daily_v2.csv")
        eth["tier1_pct"] = round(shares['tier1_share_pct'].mean(), 1)
        eth["tier2_pct"] = round(shares['tier2_share_pct'].mean(), 1)
        eth["tier3_pct"] = round(shares['tier3_share_pct'].mean(), 1)
        conc = pd.read_csv(DATA_PROC / "exhibit_C2_concentration_daily_v2.csv")
        eth["hhi"] = round(conc['tier_hhi'].mean())
        print(f"  ETH data-driven (expanded): T1={eth['tier1_pct']:.1f}%, T2={eth['tier2_pct']:.1f}%, "
              f"T3={eth['tier3_pct']:.1f}%, HHI={eth['hhi']:,}")
    except Exception as e:
        print(f"  Using hardcoded expanded values (could not load v2: {e})")
    return eth


def main():
    print("Exhibit 22: Tron vs. Ethereum Control Layer Comparison\n")

    summary, tron_csv = load_tron_data()

    # ── Ethereum data (data-driven from exhibit_C, with fallback) ──
    eth = load_eth_data_driven()

    # ── Tron data (from v3 summary) ──
    tron_identified_pct = summary["identified"]["pct"]
    tron_dark_pct = summary["dark"]["pct"]

    # Consolidate Tron entities by type
    tron_by_entity = summary["by_entity"]
    # All identified are exchanges except Sun (DeFi/DEX)
    tron_exchange_val = sum(v["value"] for k, v in tron_by_entity.items() if "Sun" not in k)
    tron_defi_val = tron_by_entity.get("Sun", {}).get("value", 0)
    tron_dark_val = summary["dark"]["value"]
    tron_total = summary["total"]["value"]

    tron_exchange_pct = tron_exchange_val / tron_total * 100
    tron_defi_pct = tron_defi_val / tron_total * 100

    print(f"  Tron: {summary['identified']['count']} of {summary['total']['count']} identified "
          f"({tron_identified_pct:.1f}% by value)")
    print(f"  Tron exchange share: {tron_exchange_pct:.1f}%, DeFi: {tron_defi_pct:.1f}%, "
          f"Dark: {tron_dark_pct:.1f}%")

    # ── Build the figure: 2-column, 3-row layout ──
    setup_plot_style()
    fig, axes = plt.subplots(3, 2, figsize=(10, 10))
    fig.suptitle("Control Layer Comparison: Ethereum vs. Tron",
                 fontsize=14, fontweight="bold", y=0.97)

    # Subtitle annotation
    fig.text(0.5, 0.935,
             'Same token (USDT), different control layers: Ethereum routes through\n'
             '19 entities (6 Tier 1); Tron routes through Tier 2 exchanges with 40% dark volume',
             ha='center', va='top', fontsize=9, fontstyle='italic', color='#555555')

    c_tier1 = color("tier1")
    c_tier2 = color("tier2")
    c_tier3 = color("tier3")
    c_dark = "#444444"
    c_defi = color("positive")

    # ═══════════════════════════════════════════
    # ROW 1: Entity composition (horizontal stacked bars)
    # ═══════════════════════════════════════════
    ax_e1 = axes[0, 0]
    ax_t1 = axes[0, 1]

    # Ethereum tier distribution — stacked horizontal bar
    bar_h = 0.4
    eth_segs = [
        (eth["tier1_pct"], c_tier1, f'Tier 1: {eth["tier1_pct"]:.0f}%'),
        (eth["tier3_pct"], c_tier3, f'Tier 3: {eth["tier3_pct"]:.1f}%'),
        (eth["tier2_pct"], c_tier2, f'Tier 2: {eth["tier2_pct"]:.1f}%'),
    ]
    above_offsets = [0, 0.15, 0.30]  # stagger: Tier3 middle, Tier2 highest
    left = 0
    for idx, (width, clr, label) in enumerate(eth_segs):
        ax_e1.barh([0], [width], left=[left], color=clr, height=bar_h, edgecolor='white', linewidth=1.5)
        if width > 20:
            ax_e1.text(left + width / 2, 0, label, ha='center', va='center',
                       fontsize=9, fontweight='bold', color='white')
        else:
            # Place above bar for narrow segments, staggered heights
            y_off = bar_h / 2 + above_offsets[idx]
            ax_e1.annotate(label, xy=(left + width / 2, bar_h / 2 + 0.02),
                           xytext=(left + width / 2, y_off),
                           fontsize=8, fontweight='bold', color=clr, ha='center', va='bottom',
                           arrowprops=dict(arrowstyle='-', color=clr, lw=0.8))
        left += width
    ax_e1.set_xlim(0, 100)
    ax_e1.set_ylim(-0.55, 0.8)
    ax_e1.set_title("Ethereum: Gateway Tier Distribution", fontsize=11, fontweight="bold", pad=10)
    ax_e1.set_xlabel("% of Monitored Volume")
    ax_e1.set_yticks([])
    ax_e1.grid(False)
    # HHI annotation below bar
    ax_e1.text(50, -0.35, f"HHI: {eth['hhi']:,}", ha='center', va='center',
               fontsize=10, fontweight='bold', color=c_tier1,
               bbox=dict(boxstyle='round,pad=0.3', facecolor='#EEF2F7', edgecolor=c_tier1, alpha=0.8))

    # Tron composition — stacked horizontal bar
    tron_segs = [
        (tron_exchange_pct, c_tier2, f'Exchanges: {tron_exchange_pct:.0f}%'),
        (tron_defi_pct, c_defi, f'DeFi: {tron_defi_pct:.1f}%'),
        (tron_dark_pct, c_dark, f'Dark: {tron_dark_pct:.1f}%'),
    ]
    left = 0
    for width, clr, label in tron_segs:
        ax_t1.barh([0], [width], left=[left], color=clr, height=bar_h, edgecolor='white', linewidth=1.5)
        if width > 15:
            ax_t1.text(left + width / 2, 0, label, ha='center', va='center',
                       fontsize=9, fontweight='bold', color='white')
        else:
            # Place above bar for narrow segments
            ax_t1.annotate(label, xy=(left + width / 2, bar_h / 2 + 0.02),
                           xytext=(left + width / 2, bar_h / 2 + 0.15),
                           fontsize=8, fontweight='bold', color=clr, ha='center', va='bottom',
                           arrowprops=dict(arrowstyle='-', color=clr, lw=0.8))
        left += width
    ax_t1.set_xlim(0, 100)
    ax_t1.set_ylim(-0.5, 0.6)
    ax_t1.set_title("Tron: Gateway Composition", fontsize=11, fontweight="bold", pad=10)
    ax_t1.set_xlabel("% of Total Volume")
    ax_t1.set_yticks([])
    ax_t1.grid(False)
    # No Tier 1 annotation below bar
    ax_t1.text(50, -0.35, "No Tier 1 presence", ha='center', va='center',
               fontsize=10, fontweight='bold', color=color("stress"),
               bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFF0F0', edgecolor=color("stress"), alpha=0.8))

    # ═══════════════════════════════════════════
    # ROW 2: Address observability (stacked bar)
    # ═══════════════════════════════════════════
    ax_e2 = axes[1, 0]
    ax_t2 = axes[1, 1]

    # Ethereum observability
    bar_width = 0.5
    ax_e2.barh(["Ethereum"], [eth["label_rate"]], color=c_tier1, height=bar_width,
               label="Labeled", edgecolor='white')
    ax_e2.barh(["Ethereum"], [100 - eth["label_rate"]], left=[eth["label_rate"]],
               color=c_tier3, height=bar_width, label="Unlabeled", edgecolor='white')
    ax_e2.text(eth["label_rate"] / 2, 0, f'{eth["label_rate"]:.0f}%', ha='center', va='center',
               fontsize=12, fontweight='bold', color='white')
    ax_e2.text(eth["label_rate"] - 3, 0, f'{100 - eth["label_rate"]:.0f}%',
               ha='left', va='center', fontsize=10, fontweight='bold', color='#666666')
    ax_e2.set_xlim(0, 105)
    ax_e2.set_title("Address Observability", fontsize=11, fontweight="bold")
    ax_e2.set_xlabel("% of Volume")
    ax_e2.legend(loc="lower right", fontsize=8)
    ax_e2.grid(False)
    ax_e2.set_yticks([])

    # Tron observability
    ax_t2.barh(["Tron"], [tron_identified_pct], color=c_tier2, height=bar_width,
               label="Identified", edgecolor='white')
    ax_t2.barh(["Tron"], [tron_dark_pct], left=[tron_identified_pct],
               color=c_dark, height=bar_width, label="Dark / Unidentified", edgecolor='white')
    ax_t2.text(tron_identified_pct / 2, 0, f'{tron_identified_pct:.1f}%', ha='center', va='center',
               fontsize=12, fontweight='bold', color='white')
    ax_t2.text(tron_identified_pct + tron_dark_pct / 2, 0, f'{tron_dark_pct:.1f}%',
               ha='center', va='center', fontsize=12, fontweight='bold', color='white')
    ax_t2.set_xlim(0, 100)
    ax_t2.set_title("Address Observability", fontsize=11, fontweight="bold")
    ax_t2.set_xlabel("% of Volume")
    ax_t2.legend(loc="lower right", fontsize=8)
    ax_t2.grid(False)
    ax_t2.set_yticks([])

    # ═══════════════════════════════════════════
    # ROW 3: Gateway type distribution (horizontal bars)
    # ═══════════════════════════════════════════
    ax_e3 = axes[2, 0]
    ax_t3 = axes[2, 1]

    # Ethereum gateway types — from expanded registry volume summary
    eth_types = ["Issuers", "Exchanges", "DeFi Protocols", "DEX Aggregators"]
    try:
        gs = pd.read_csv(DATA_PROC / "gateway_volume_summary_v2.csv")
        total_vol = gs['total_volume'].sum()
        issuers_v = gs[gs['entity'].isin(['Circle', 'Tether', 'Paxos'])]['total_volume'].sum()
        exchanges_v = gs[gs['entity'].isin(['Binance', 'Coinbase', 'Kraken', 'OKX', 'Bybit',
                                            'Gemini', 'BitGo', 'Robinhood', 'PayPal'])]['total_volume'].sum()
        defi_v = gs[gs['entity'].isin(['Curve 3pool', 'Aave V3', 'Compound V3'])]['total_volume'].sum()
        dex_v = gs[gs['entity'].isin(['Uniswap V3', 'Uniswap Universal Router',
                                       '1inch', 'Tornado Cash'])]['total_volume'].sum()
        eth_type_pcts = [issuers_v/total_vol*100, exchanges_v/total_vol*100,
                         defi_v/total_vol*100, dex_v/total_vol*100]
    except Exception:
        eth_type_pcts = [23.8, 73.1, 1.9, 1.2]
    eth_type_colors = [c_tier1, c_tier2, c_tier3, "#BBBBBB"]
    bars_e = ax_e3.barh(eth_types, eth_type_pcts, color=eth_type_colors, height=0.6,
                         edgecolor='white')
    for bar, val in zip(bars_e, eth_type_pcts):
        x_pos = max(bar.get_width() + 1, 2)
        ax_e3.text(x_pos, bar.get_y() + bar.get_height() / 2,
                   f'{val:.1f}%', ha='left', va='center', fontsize=8, fontweight='bold')
    ax_e3.set_title("Gateway Type Distribution", fontsize=11, fontweight="bold")
    ax_e3.set_xlabel("% of Monitored Volume")
    ax_e3.set_xlim(0, 80)
    ax_e3.invert_yaxis()
    ax_e3.grid(axis='x', alpha=0.3)

    # Tron gateway types
    # Build from v3 data
    tron_entities = []
    for entity_name, entity_data in sorted(tron_by_entity.items(),
                                            key=lambda x: x[1]["value"], reverse=True):
        clean_name = entity_name.split(":")[0].strip()
        if clean_name.startswith("Bybit"):
            # Aggregate Bybit entries
            existing = [e for e in tron_entities if e[0] == "Bybit"]
            if existing:
                existing[0][1] += entity_data["value"] / tron_total * 100
                existing[0][2] += entity_data["count"]
                continue
            else:
                clean_name = "Bybit"
        pct = entity_data["value"] / tron_total * 100
        tron_entities.append([clean_name, pct, entity_data["count"]])

    # Sort by percentage
    tron_entities.sort(key=lambda x: x[1], reverse=True)
    # Add dark layer
    tron_entities.append(["Unidentified (dark)", tron_dark_pct, summary["dark"]["count"]])

    tron_type_names = [e[0] for e in tron_entities]
    tron_type_pcts = [e[1] for e in tron_entities]
    tron_type_colors_list = []
    for name in tron_type_names:
        if name == "Unidentified (dark)":
            tron_type_colors_list.append(c_dark)
        elif name in ("Sun",):
            tron_type_colors_list.append(c_defi)
        else:
            tron_type_colors_list.append(c_tier2)

    bars_t = ax_t3.barh(tron_type_names, tron_type_pcts, color=tron_type_colors_list,
                         height=0.6, edgecolor='white')
    for bar, val in zip(bars_t, tron_type_pcts):
        if val > 1.5:
            ax_t3.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                       f'{val:.1f}%', ha='left', va='center', fontsize=8, fontweight='bold')
    ax_t3.set_title("Entity Distribution", fontsize=11, fontweight="bold")
    ax_t3.set_xlabel("% of Total Volume")
    ax_t3.set_xlim(0, 50)
    ax_t3.invert_yaxis()
    ax_t3.grid(axis='x', alpha=0.3)

    # ── Summary stats boxes ──
    # Ethereum stats
    eth_stats = (f"ETH Summary\n"
                 f"  {eth['label_rate']:.0f}% labeled  |  HHI: {eth['hhi']:,}\n"
                 f"  {eth['n_gateways']} gateways  |  {eth['n_tier1']} Tier 1")
    fig.text(0.25, 0.055, eth_stats, ha='center', va='bottom', fontsize=8,
             fontfamily='monospace',
             bbox=dict(boxstyle='round,pad=0.4', facecolor='#EEF2F7',
                       edgecolor=c_tier1, alpha=0.9))

    # Tron stats
    tron_stats = (f"TRON Summary\n"
                  f"  59.6% labeled  |  HHI: ~10,000\n"
                  f"  3 principal gateways  |  0 Tier 1")
    fig.text(0.75, 0.055, tron_stats, ha='center', va='bottom', fontsize=8,
             fontfamily='monospace',
             bbox=dict(boxstyle='round,pad=0.4', facecolor='#FFF0F0',
                       edgecolor=color("stress"), alpha=0.9))

    fig.tight_layout(rect=[0, 0.11, 1, 0.92])

    save_exhibit(fig, "exhibit22_tron_vs_eth_comparison.png",
                 "Source: Dune Analytics (Ethereum: 51 addresses, 19 entities), Nansen/Tronscan "
                 "(Tron: 30 addresses). "
                 f"Tron: 16 of 30 identified ({tron_identified_pct:.1f}% by value). "
                 "Authors' calculations.")
    print("\u2713 Exhibit 22 saved")


if __name__ == "__main__":
    main()
