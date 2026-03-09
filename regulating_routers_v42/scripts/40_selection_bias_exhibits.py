"""v26 Selection Bias Exhibits: Empirical grounding for selection bias defense.

Generates:
  - media/exhibit_sb1_unlabeled_degree.png   (SB-1: degree vs flow symmetry scatter)
  - media/exhibit_sb2_size_distribution.png   (SB-2: transfer size distribution)
  - data/processed/selection_bias_summary_stats.json

Requires Dune query outputs from 41_selection_bias_dune.py:
  - data/raw/dune_transfer_size_distribution.csv
  - data/raw/dune_unlabeled_top500_degree.csv
  - data/raw/dune_labeled_gateway_degree.csv
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
import json
import warnings
warnings.filterwarnings('ignore')

# ── Paths ────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
MEDIA = ROOT / 'media'
DATA_RAW = ROOT / 'data' / 'raw'
DATA_PROC = ROOT / 'data' / 'processed'

# ── Fed paper aesthetic ──────────────────────────────────────
FED_NAVY = '#1B2A4A'
FED_BLUE = '#336699'
FED_LIGHT = '#6699CC'
FED_RED = '#CC3333'
FED_GOLD = '#CC9933'
FED_GRAY = '#808080'
FED_DARK = '#404040'

def apply_style():
    plt.rcParams.update({
        'font.family': 'serif',
        'font.size': 10,
        'axes.titlesize': 11,
        'axes.titleweight': 'bold',
        'axes.labelsize': 10,
        'xtick.labelsize': 9,
        'ytick.labelsize': 9,
        'legend.fontsize': 8.5,
        'figure.dpi': 300,
        'savefig.dpi': 300,
        'savefig.bbox': 'tight',
        'axes.spines.top': False,
        'axes.spines.right': False,
    })

def add_source(fig, text="Source: Authors' calculations using Dune Analytics data."):
    fig.text(0.02, 0.01, text, fontsize=7, fontstyle='italic', color='#666666')

def save(fig, name):
    path = MEDIA / name
    fig.savefig(path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"  Saved: {path}")


# ── Load data ────────────────────────────────────────────────

def load_sb2():
    return pd.read_csv(DATA_RAW / 'dune_transfer_size_distribution.csv')

def load_sb1a():
    return pd.read_csv(DATA_RAW / 'dune_unlabeled_top500_degree.csv')

def load_sb1b():
    df = pd.read_csv(DATA_RAW / 'dune_labeled_gateway_degree.csv')
    # Merge with registry for entity names
    try:
        reg = pd.read_csv(DATA_PROC / 'gateway_registry_expanded.csv')
        reg['address'] = reg['address'].str.lower()
        df['address'] = df['address'].str.lower()
        df = df.merge(reg[['address', 'entity', 'tier']].drop_duplicates('address'),
                      on='address', how='left')
    except Exception:
        pass
    return df


# ── Exhibit SB-1: Degree vs Flow Symmetry ───────────────────

def exhibit_sb1():
    """Scatter plot: counterparty degree vs flow symmetry for labeled vs unlabeled."""
    print("\n  Generating Exhibit SB-1: Network degree vs flow symmetry")

    unlabeled = load_sb1a()
    labeled = load_sb1b()

    # Compute combined degree (max of in/out)
    unlabeled['degree'] = unlabeled[['in_degree', 'out_degree']].max(axis=1)
    labeled['degree'] = labeled[['in_degree', 'out_degree']].max(axis=1)

    # Filter out zero-volume addresses
    unlabeled = unlabeled[unlabeled['total_volume_usd'] > 0]
    labeled = labeled[labeled['total_volume_usd'] > 0]

    apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))

    # Panel A: Degree vs Volume scatter
    ax = axes[0]
    # Unlabeled — size scaled by log volume
    ul_sizes = np.clip(np.log10(unlabeled['total_volume_usd'].clip(lower=1)) * 3, 5, 50)
    ax.scatter(unlabeled['degree'], unlabeled['total_volume_usd'] / 1e9,
               s=ul_sizes, alpha=0.35, color=FED_LIGHT, edgecolors='none',
               label='Unlabeled (top 500)', zorder=2)
    # Labeled
    lb_sizes = np.clip(np.log10(labeled['total_volume_usd'].clip(lower=1)) * 3, 8, 80)
    ax.scatter(labeled['degree'], labeled['total_volume_usd'] / 1e9,
               s=lb_sizes, alpha=0.8, color=FED_NAVY, edgecolors='white',
               linewidth=0.5, label='Labeled gateways (51)', zorder=3)

    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel('Max Counterparty Degree (log scale)')
    ax.set_ylabel('Total Volume, $B (log scale)')
    ax.set_title('A. Network Degree vs. Volume')
    ax.legend(loc='lower right', framealpha=0.9)
    ax.grid(True, alpha=0.3, linestyle='--')

    # Panel B: Flow symmetry distribution
    ax = axes[1]
    bins = np.linspace(0, 1.0, 25)
    ax.hist(unlabeled['flow_symmetry'], bins=bins, alpha=0.5, color=FED_LIGHT,
            label='Unlabeled (top 500)', density=True, zorder=2)
    ax.hist(labeled['flow_symmetry'], bins=bins, alpha=0.7, color=FED_NAVY,
            label='Labeled gateways', density=True, zorder=3)
    ax.axvline(0.9, color=FED_RED, linestyle='--', linewidth=1, alpha=0.7,
               label='Symmetry threshold (0.9)')
    ax.set_xlabel('Flow Symmetry (inflow/outflow ratio)')
    ax.set_ylabel('Density')
    ax.set_title('B. Flow Symmetry Distribution')
    ax.legend(loc='upper left', framealpha=0.9)
    ax.grid(True, alpha=0.3, linestyle='--')

    fig.suptitle('Selection Bias Analysis: Behavioral Signatures of Unlabeled Addresses',
                 fontsize=12, fontweight='bold', y=1.02)
    add_source(fig, "Source: Dune Analytics, Jul 2024\u2013Jan 2025 (6-month sample). "
               "Labeled set: 51 gateway addresses from expanded registry.")
    fig.tight_layout()
    save(fig, 'exhibit_sb1_unlabeled_degree.png')

    # Compute summary stats
    ul_high_sym = (unlabeled['flow_symmetry'] >= 0.9).sum()
    ul_high_deg = (unlabeled['degree'] >= 100).sum()
    ul_gateway_like = ((unlabeled['flow_symmetry'] >= 0.9) & (unlabeled['degree'] >= 100)).sum()
    lb_high_sym = (labeled['flow_symmetry'] >= 0.9).sum()

    return {
        'unlabeled_n': len(unlabeled),
        'labeled_n': len(labeled),
        'unlabeled_median_degree': int(unlabeled['degree'].median()),
        'labeled_median_degree': int(labeled['degree'].median()),
        'unlabeled_median_flow_symmetry': round(float(unlabeled['flow_symmetry'].median()), 4),
        'labeled_median_flow_symmetry': round(float(labeled['flow_symmetry'].median()), 4),
        'unlabeled_high_symmetry_pct': round(ul_high_sym / len(unlabeled) * 100, 1),
        'unlabeled_high_degree_pct': round(ul_high_deg / len(unlabeled) * 100, 1),
        'unlabeled_gateway_like_pct': round(ul_gateway_like / len(unlabeled) * 100, 1),
        'labeled_high_symmetry_pct': round(lb_high_sym / len(labeled) * 100, 1),
    }


# ── Exhibit SB-2: Transfer Size Distribution ────────────────

def exhibit_sb2():
    """Grouped bar chart: transfer size distribution, labeled vs unlabeled."""
    print("\n  Generating Exhibit SB-2: Transfer size distribution")

    df = load_sb2()

    # Parse size buckets for ordering
    bucket_labels = {
        '1_lt_100': '<$100',
        '2_100_1k': '$100\u2013$1K',
        '3_1k_10k': '$1K\u2013$10K',
        '4_10k_100k': '$10K\u2013$100K',
        '5_100k_1m': '$100K\u2013$1M',
        '6_1m_10m': '$1M\u2013$10M',
        '7_10m_plus': '$10M+',
    }

    apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))

    for panel_idx, (metric, metric_label) in enumerate([
        ('total_volume_usd', 'Share of Volume (%)'),
        ('n_transfers', 'Share of Transfers (%)')
    ]):
        ax = axes[panel_idx]
        x = np.arange(len(bucket_labels))
        width = 0.35

        for cat_idx, (cat, cat_color, cat_label) in enumerate([
            ('labeled', FED_NAVY, 'Labeled (51 gateways)'),
            ('unlabeled', FED_LIGHT, 'Unlabeled'),
        ]):
            sub = df[df['address_category'] == cat].set_index('size_bucket')
            total = sub[metric].sum()
            vals = [sub.loc[bk, metric] / total * 100 if bk in sub.index else 0
                    for bk in bucket_labels.keys()]
            offset = -width/2 + cat_idx * width
            ax.bar(x + offset, vals, width, label=cat_label, color=cat_color,
                   alpha=0.85, edgecolor='white', linewidth=0.5)

        ax.set_xticks(x)
        ax.set_xticklabels(bucket_labels.values(), rotation=35, ha='right', fontsize=8)
        ax.set_ylabel(metric_label)
        title_letter = 'A' if panel_idx == 0 else 'B'
        title_suffix = 'by Volume' if panel_idx == 0 else 'by Transfer Count'
        ax.set_title('{0}. Distribution {1}'.format(title_letter, title_suffix))
        ax.legend(loc='upper left' if panel_idx == 0 else 'upper right', framealpha=0.9)
        ax.grid(True, alpha=0.3, linestyle='--', axis='y')

    fig.suptitle('Transfer Size Distribution: Labeled vs. Unlabeled Addresses',
                 fontsize=12, fontweight='bold', y=1.02)
    add_source(fig, "Source: Dune Analytics, Jul 2024\u2013Jan 2025. "
               "USDC + USDT transfers on Ethereum mainnet.")
    fig.tight_layout()
    save(fig, 'exhibit_sb2_size_distribution.png')

    # Compute volume and transfer stats
    labeled = df[df['address_category'] == 'labeled']
    unlabeled = df[df['address_category'] == 'unlabeled']
    lab_vol = labeled['total_volume_usd'].sum()
    unlab_vol = unlabeled['total_volume_usd'].sum()
    lab_n = labeled['n_transfers'].sum()
    unlab_n = unlabeled['n_transfers'].sum()

    # Large transfer share (>=1M)
    lab_large = labeled[labeled['size_bucket'].isin(['6_1m_10m', '7_10m_plus'])]['total_volume_usd'].sum()
    unlab_large = unlabeled[unlabeled['size_bucket'].isin(['6_1m_10m', '7_10m_plus'])]['total_volume_usd'].sum()

    # Small transfer share (<$1K by count)
    lab_small_n = labeled[labeled['size_bucket'].isin(['1_lt_100', '2_100_1k'])]['n_transfers'].sum()
    unlab_small_n = unlabeled[unlabeled['size_bucket'].isin(['1_lt_100', '2_100_1k'])]['n_transfers'].sum()

    return {
        'labeled_volume_T': round(lab_vol / 1e12, 2),
        'unlabeled_volume_T': round(unlab_vol / 1e12, 2),
        'unlabeled_volume_share_pct': round(unlab_vol / (lab_vol + unlab_vol) * 100, 1),
        'labeled_transfers_M': round(lab_n / 1e6, 1),
        'unlabeled_transfers_M': round(unlab_n / 1e6, 1),
        'labeled_large_vol_share_pct': round(lab_large / lab_vol * 100, 1),
        'unlabeled_large_vol_share_pct': round(unlab_large / unlab_vol * 100, 1),
        'labeled_small_count_share_pct': round(lab_small_n / lab_n * 100, 1),
        'unlabeled_small_count_share_pct': round(unlab_small_n / unlab_n * 100, 1),
        'sample_window': 'Jul 2024 - Jan 2025 (6 months)',
    }


# ── Main ─────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("v26 SELECTION BIAS EXHIBITS")
    print("=" * 60)

    results = {}

    # SB-2 first (minimum viable)
    try:
        sb2_stats = exhibit_sb2()
        results['sb2'] = sb2_stats
        print("\n  SB-2 Stats:")
        print("    Labeled volume: ${0}T ({1}M transfers)".format(
            sb2_stats['labeled_volume_T'], sb2_stats['labeled_transfers_M']))
        print("    Unlabeled volume: ${0}T ({1}M transfers)".format(
            sb2_stats['unlabeled_volume_T'], sb2_stats['unlabeled_transfers_M']))
        print("    Unlabeled volume share: {0}%".format(sb2_stats['unlabeled_volume_share_pct']))
        print("    Labeled >=1M vol share: {0}%".format(sb2_stats['labeled_large_vol_share_pct']))
        print("    Unlabeled >=1M vol share: {0}%".format(sb2_stats['unlabeled_large_vol_share_pct']))
        print("    Labeled <$1K count share: {0}%".format(sb2_stats['labeled_small_count_share_pct']))
        print("    Unlabeled <$1K count share: {0}%".format(sb2_stats['unlabeled_small_count_share_pct']))
    except Exception as e:
        print(f"  SB-2 FAILED: {e}")

    # SB-1 (full version)
    try:
        sb1_stats = exhibit_sb1()
        results['sb1'] = sb1_stats
        print("\n  SB-1 Stats:")
        print("    Unlabeled median degree: {0}".format(sb1_stats['unlabeled_median_degree']))
        print("    Labeled median degree: {0}".format(sb1_stats['labeled_median_degree']))
        print("    Unlabeled median flow symmetry: {0}".format(
            sb1_stats['unlabeled_median_flow_symmetry']))
        print("    Labeled median flow symmetry: {0}".format(
            sb1_stats['labeled_median_flow_symmetry']))
        print("    Unlabeled gateway-like (sym>=0.9, deg>=100): {0}%".format(
            sb1_stats['unlabeled_gateway_like_pct']))
    except Exception as e:
        print(f"  SB-1 FAILED: {e}")

    # Construct interpretation
    if 'sb2' in results and 'sb1' in results:
        sb2 = results['sb2']
        sb1 = results['sb1']
        results['interpretation'] = (
            "The unlabeled addresses differ structurally from labeled gateways in two ways. "
            "First, unlabeled transfers are less concentrated in large transactions: "
            "{0}% of unlabeled volume is in transfers >= $1M versus {1}% for labeled "
            "(a {2:.1f} pp gap). Second, {3}% of unlabeled <$1K transfers by count versus "
            "{4}% for labeled, consistent with a heavier P2P footprint. "
            "Among the top 500 unlabeled addresses by volume, {5}% exhibit gateway-like "
            "behavioral signatures (flow symmetry >= 0.9 and degree >= 100), indicating "
            "that some unlabeled volume is indeed exchange-like but the majority is "
            "structurally distinct.".format(
                sb2['unlabeled_large_vol_share_pct'],
                sb2['labeled_large_vol_share_pct'],
                sb2['labeled_large_vol_share_pct'] - sb2['unlabeled_large_vol_share_pct'],
                sb2['unlabeled_small_count_share_pct'],
                sb2['labeled_small_count_share_pct'],
                sb1['unlabeled_gateway_like_pct'],
            )
        )
        print("\n  Interpretation:")
        print("    " + results['interpretation'])

    # Save summary stats
    out_path = DATA_PROC / 'selection_bias_summary_stats.json'
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
