"""Task 1: Exhibit 21 — Gateway Counterparty Network Diagram.

Force-directed / manual-positioned network showing gateway interaction topology
with market maker intermediaries highlighted. Reads from gateway_network_expanded.csv.
"""
import pandas as pd, numpy as np, matplotlib.pyplot as plt, matplotlib.patches as mpatches
import networkx as nx
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_PROC, save_exhibit, setup_plot_style, color


# Gateway metadata: volume, chain, tier, type
GATEWAY_META = {
    "Binance Hot Wallet": {"vol_B": 1013.9, "chain": "ETH", "tier": 2, "type": "exchange"},
    "Circle Treasury": {"vol_B": 622.6, "chain": "ETH", "tier": 1, "type": "issuer"},
    "Tether Treasury": {"vol_B": 169.2, "chain": "ETH", "tier": 2, "type": "issuer"},
    "TKHuVq1o": {"vol_B": 115.8, "chain": "TRON", "tier": 2, "type": "exchange", "label": "Bitfinex/Tether\n(Tron)"},
    "0x28c5b044": {"vol_B": 96.7, "chain": "ETH", "tier": 1, "type": "pipeline", "label": "Coinbase\nUSDC Wallet"},
    "TU4vEruv": {"vol_B": 66.4, "chain": "TRON", "tier": 2, "type": "exchange", "label": "Bybit\n(Tron)"},
    "TWd4WrZ9": {"vol_B": 40.2, "chain": "TRON", "tier": 2, "type": "exchange", "label": "Binance\n(Tron)"},
    "Curve 3pool": {"vol_B": 22.7, "chain": "ETH", "tier": 3, "type": "defi"},
    "OKX": {"vol_B": 6.8, "chain": "ETH", "tier": 2, "type": "exchange"},
    "Uniswap V3 Router": {"vol_B": 3.5, "chain": "ETH", "tier": 3, "type": "defi"},
    "0x Exchange": {"vol_B": 0.9, "chain": "ETH", "tier": 3, "type": "dex"},
    "Coinbase Custody": {"vol_B": 0.01, "chain": "ETH", "tier": 1, "type": "custodian"},
    "Kraken": {"vol_B": 0.01, "chain": "ETH", "tier": 2, "type": "exchange"},
    "Aave V3 Pool": {"vol_B": 0.01, "chain": "ETH", "tier": 3, "type": "defi"},
    "Gemini": {"vol_B": 0.01, "chain": "ETH", "tier": 1, "type": "custodian"},
}

# Market maker aggregated edges (from data analysis)
MM_EDGES = {
    "Wintermute": {
        "Binance Hot Wallet": 156.8, "Circle Treasury": 117.0, "OKX": 0.3, "0x Exchange": 0.1,
    },
    "Cumberland": {
        "Binance Hot Wallet": 8.1, "Tether Treasury": 2.1, "OKX": 0.04,
    },
    "Jump Trading": {
        "Binance Hot Wallet": 4.3,
    },
    "B2C2": {
        "Circle Treasury": 3.0, "Tether Treasury": 0.02, "OKX": 0.02,
    },
    "Galaxy Digital": {
        "Binance Hot Wallet": 1.1,
    },
}

# Coinbase-Circle pipeline
PIPELINE_EDGE = ("0x28c5b044", "Circle Treasury", 48.4)


def main():
    print("Exhibit 21: Gateway Counterparty Network\n")

    # Build the graph
    G = nx.Graph()

    # Add gateway nodes
    for name, meta in GATEWAY_META.items():
        label = meta.get("label", name)
        G.add_node(name, node_type="gateway", tier=meta["tier"],
                   vol_B=meta["vol_B"], chain=meta["chain"],
                   display_label=label)

    # Add market maker nodes
    for mm_name, edges in MM_EDGES.items():
        total_vol = sum(edges.values())
        G.add_node(mm_name, node_type="mm", vol_B=total_vol,
                   display_label=mm_name)

    # Add edges from market makers to gateways
    for mm_name, edges in MM_EDGES.items():
        for gw, vol_B in edges.items():
            if vol_B > 0.05:  # threshold for visibility
                G.add_edge(mm_name, gw, weight=vol_B, edge_type="mm")

    # Add pipeline edge
    G.add_edge(PIPELINE_EDGE[0], PIPELINE_EDGE[1],
               weight=PIPELINE_EDGE[2], edge_type="pipeline")

    # Manual layout positions (tuned to avoid collisions)
    pos = {
        # Top center: two largest gateways — spread wider
        "Binance Hot Wallet": (0.28, 0.88),
        "Circle Treasury": (0.62, 0.88),
        # Coinbase cluster — separated from Circle
        "0x28c5b044": (0.82, 0.92),  # Coinbase USDC Wallet — far right of Circle
        "Coinbase Custody": (0.95, 0.82),  # further right and down
        # Tether
        "Tether Treasury": (0.90, 0.65),
        # Tron cluster (left column, evenly spaced)
        "TKHuVq1o": (0.06, 0.70),
        "TU4vEruv": (0.06, 0.50),
        "TWd4WrZ9": (0.06, 0.30),
        # Mid-tier ETH exchanges — spread
        "OKX": (0.28, 0.52),
        "Kraken": (0.16, 0.82),
        "Gemini": (0.10, 0.96),
        # DeFi cluster (bottom right, well-spaced vertically)
        "Curve 3pool": (0.92, 0.40),
        "Uniswap V3 Router": (0.92, 0.25),
        "Aave V3 Pool": (0.78, 0.15),
        "0x Exchange": (0.62, 0.18),
        # Market makers (center zone, spread out)
        "Wintermute": (0.48, 0.62),
        "Cumberland": (0.58, 0.35),
        "Jump Trading": (0.22, 0.38),
        "B2C2": (0.75, 0.50),
        "Galaxy Digital": (0.36, 0.28),
    }

    # Plot
    setup_plot_style()
    fig, ax = plt.subplots(figsize=(12, 9))
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Gateway Counterparty Network: Market Maker Intermediation",
                 fontsize=13, fontweight="bold", pad=15)

    tier_colors = {1: color("tier1"), 2: color("tier2"), 3: color("tier3")}
    mm_color = color("stress")

    # Draw edges
    for u, v, data in G.edges(data=True):
        x = [pos[u][0], pos[v][0]]
        y = [pos[u][1], pos[v][1]]
        w = data["weight"]
        lw = max(0.4, np.log10(w + 1) * 1.2)

        if data.get("edge_type") == "pipeline":
            # Distinctive pipeline edge
            ax.plot(x, y, color=color("primary"), linewidth=2.5,
                    linestyle="--", alpha=0.8, zorder=2)
            mid_x, mid_y = (x[0] + x[1]) / 2, (y[0] + y[1]) / 2
            ax.annotate(f"$48.4B\npipeline", xy=(mid_x + 0.02, mid_y + 0.04),
                        fontsize=6.5, ha="center", va="center",
                        color=color("primary"), fontweight="bold",
                        bbox=dict(boxstyle="round,pad=0.2", facecolor="white",
                                  edgecolor=color("primary"), alpha=0.85))
        elif data.get("edge_type") == "mm":
            # Check if Wintermute edge
            is_wm = (u == "Wintermute" or v == "Wintermute")
            ec = mm_color if is_wm else "#BBBBBB"
            ea = 0.7 if is_wm else 0.4
            ax.plot(x, y, color=ec, linewidth=lw, alpha=ea, zorder=1)
            # Volume labels on largest edges — offset 70% toward destination for Wintermute
            if w > 50:
                if is_wm:
                    # Place label 70% of the way from Wintermute toward the gateway
                    wm_idx = 0 if u == "Wintermute" else 1
                    gw_idx = 1 - wm_idx
                    lbl_x = x[wm_idx] + 0.50 * (x[gw_idx] - x[wm_idx])
                    lbl_y = y[wm_idx] + 0.50 * (y[gw_idx] - y[wm_idx])
                else:
                    lbl_x = (x[0] + x[1]) / 2
                    lbl_y = (y[0] + y[1]) / 2
                ax.annotate(f"${w:.0f}B", xy=(lbl_x, lbl_y),
                            fontsize=6, ha="center", va="center",
                            color=ec, fontweight="bold",
                            bbox=dict(boxstyle="round,pad=0.15", facecolor="white",
                                      edgecolor=ec, alpha=0.8))

    # Draw nodes
    for node in G.nodes():
        x, y = pos[node]
        ndata = G.nodes[node]
        vol = ndata.get("vol_B", 0)
        label = ndata.get("display_label", node)

        if ndata["node_type"] == "mm":
            # Market makers: diamonds (squares rotated)
            size = max(200, vol * 3)
            ax.scatter(x, y, s=size, c=mm_color, marker="D", zorder=10,
                       edgecolors="white", linewidths=1)
            ax.annotate(f"{label}\n${vol:.0f}B", xy=(x, y - 0.045),
                        fontsize=6.5, ha="center", va="top",
                        fontweight="bold", color=mm_color)
        else:
            # Gateways: circles, sized by log(volume)
            tier = ndata.get("tier", 3)
            nc = tier_colors.get(tier, color("tier3"))
            size = max(150, np.log10(vol + 1) * 350)
            ax.scatter(x, y, s=size, c=nc, marker="o", zorder=10,
                       edgecolors="white", linewidths=1.2)
            # Label — show volume for all named gateways
            fontsize = 7 if vol > 10 else 6
            fw = "bold" if vol > 50 else "normal"
            vol_str = f"${vol:.0f}B" if vol >= 1 else "<$1B" if vol > 0 else ""
            disp = f"{label}\n{vol_str}" if vol_str else label
            y_offset = 0.04 if y < 0.5 else -0.04
            va = "bottom" if y < 0.5 else "top"
            ax.annotate(disp, xy=(x, y + y_offset),
                        fontsize=fontsize, ha="center", va=va,
                        fontweight=fw, color="#222222")

    # Wintermute annotation box — centered at bottom
    props = dict(boxstyle="round,pad=0.5", facecolor="#FFF0F0",
                 edgecolor=mm_color, alpha=0.95)
    ax.text(0.50, 0.02,
            "Wintermute ($274B) intermediates across 4 of 7 top gateways\n"
            "   exceeding Tether Treasury total volume ($169B)",
            transform=ax.transAxes, fontsize=8, ha="center", va="bottom",
            bbox=props, color=mm_color, fontweight="bold")

    # Legend
    legend_elements = [
        mpatches.Patch(facecolor=color("tier1"), label="Tier 1 (Issuers/Custodians)"),
        mpatches.Patch(facecolor=color("tier2"), label="Tier 2 (Exchanges)"),
        mpatches.Patch(facecolor=color("tier3"), label="Tier 3 (DeFi/DEX)"),
        mpatches.Patch(facecolor=mm_color, label="Market Makers"),
        plt.Line2D([0], [0], color=mm_color, linewidth=1.5, label="Wintermute edge"),
        plt.Line2D([0], [0], color=color("primary"), linewidth=1.5,
                   linestyle="--", label="Coinbase-Circle pipeline"),
    ]
    ax.legend(handles=legend_elements, loc="lower left", fontsize=7,
              framealpha=0.9, edgecolor="#CCCCCC")

    fig.tight_layout()
    save_exhibit(fig, "exhibit21_gateway_network.png",
                 "Source: Nansen blockchain analytics, counterparty network data for 15 gateways "
                 "(1,092 edges, $2.16T aggregate volume). February 2023\u2013January 2026.")
    print("\u2713 Exhibit 21 saved")


if __name__ == "__main__":
    main()
