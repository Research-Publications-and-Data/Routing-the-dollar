"""Create conceptual schematic: same token, different regulatory surface."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
from pathlib import Path

MEDIA = Path(__file__).resolve().parent.parent / 'media'
MEDIA.mkdir(parents=True, exist_ok=True)

# Colors
NAVY = '#003366'
BLUE = '#4682B4'
LIGHT = '#B0C4DE'
WHITE_BG = '#F5F5F5'
RED = '#CC3333'
GREEN = '#339933'
GRAY = '#999999'

plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 11,
    'axes.titlesize': 13,
    'figure.dpi': 150,
    'savefig.dpi': 300,
})

fig, ax = plt.subplots(figsize=(13, 6.5))
ax.set_xlim(-0.15, 11)
ax.set_ylim(0, 7)
ax.axis('off')

# ── Column labels ──
ax.text(0.8, 6.6, 'TOKEN LAYER', fontsize=12, fontweight='bold', color=GRAY,
        ha='center', va='center')
ax.text(3.5, 6.6, 'GATEWAY', fontsize=12, fontweight='bold', color=GRAY,
        ha='center', va='center')
ax.text(6.0, 6.6, 'CHAIN', fontsize=12, fontweight='bold', color=GRAY,
        ha='center', va='center')
ax.text(9.0, 6.6, 'REGULATORY SURFACE', fontsize=12, fontweight='bold', color=GRAY,
        ha='center', va='center')

# ── Token box (left) ──
token_box = FancyBboxPatch((0.1, 2.5), 1.4, 2.0, boxstyle="round,pad=0.15",
                            facecolor=WHITE_BG, edgecolor=NAVY, linewidth=2)
ax.add_patch(token_box)
ax.text(0.8, 3.9, 'USDC', fontsize=14, fontweight='bold', color=NAVY, ha='center', va='center')
ax.text(0.8, 3.4, 'or USDT', fontsize=12, color=NAVY, ha='center', va='center')
ax.text(0.8, 2.85, '(same token)', fontsize=9, fontstyle='italic', color=GRAY, ha='center', va='center')

# ── Gateway A: Tier 1 ──
gw_a = FancyBboxPatch((2.6, 5.0), 1.8, 1.2, boxstyle="round,pad=0.12",
                       facecolor=NAVY, edgecolor=NAVY, linewidth=1.5, alpha=0.9)
ax.add_patch(gw_a)
ax.text(3.5, 5.85, 'Circle', fontsize=11, fontweight='bold', color='white', ha='center')
ax.text(3.5, 5.45, 'CLII 0.92, Tier 1', fontsize=9, color='#B0C4DE', ha='center')

# ── Gateway B: Tier 2 ──
gw_b = FancyBboxPatch((2.6, 2.9), 1.8, 1.2, boxstyle="round,pad=0.12",
                       facecolor=BLUE, edgecolor=BLUE, linewidth=1.5, alpha=0.9)
ax.add_patch(gw_b)
ax.text(3.5, 3.75, 'Binance', fontsize=11, fontweight='bold', color='white', ha='center')
ax.text(3.5, 3.35, 'CLII 0.38, Tier 2', fontsize=9, color='#D4E4F4', ha='center')

# ── Gateway C: Tier 3 ──
gw_c = FancyBboxPatch((2.6, 0.8), 1.8, 1.2, boxstyle="round,pad=0.12",
                       facecolor=LIGHT, edgecolor=GRAY, linewidth=1.5)
ax.add_patch(gw_c)
ax.text(3.5, 1.65, 'Curve 3pool', fontsize=11, fontweight='bold', color=NAVY, ha='center')
ax.text(3.5, 1.25, 'CLII 0.18, Tier 3', fontsize=9, color='#555555', ha='center')

# ── Chain boxes ──
# Ethereum (for all three)
for y, label in [(5.3, 'Ethereum'), (3.55, 'Ethereum'), (3.0, 'Tron'), (1.15, 'Ethereum')]:
    chain_box = FancyBboxPatch((5.2, y - 0.25), 1.6, 0.5, boxstyle="round,pad=0.08",
                                facecolor='white', edgecolor=NAVY, linewidth=1)
    ax.add_patch(chain_box)
    ax.text(6.0, y, label, fontsize=10, ha='center', va='center', color=NAVY)

# ── Regulatory surface boxes ──
surfaces = [
    (5.3, ['Licensed issuer', 'Monthly audits', 'Freeze-capable', 'OFAC-compliant'], GREEN),
    (3.55, ['Offshore exchange', 'Partial compliance', 'DOJ settlement'], '#CC8800'),
    (3.0, ['Zero Tier 1 routing', '58% Tier 3', '40% unattributed'], RED),
    (1.15, ['Permissionless', 'No KYC / No freeze', 'No identity layer'], RED),
]
for y, labels, border_color in surfaces:
    h = 0.14 * len(labels) + 0.3
    reg_box = FancyBboxPatch((7.5, y - h/2), 2.6, h, boxstyle="round,pad=0.1",
                              facecolor='white', edgecolor=border_color, linewidth=1.5)
    ax.add_patch(reg_box)
    for i, lbl in enumerate(labels):
        ax.text(8.8, y + (len(labels)/2 - i - 0.5) * 0.17, lbl,
                fontsize=8.5, ha='center', va='center', color='#333333')

# ── Arrows ──
arrow_kw = dict(arrowstyle='->', color=NAVY, lw=1.5, mutation_scale=15)

# Token -> Gateways
for gy in [5.6, 3.5, 1.4]:
    ax.annotate('', xy=(2.6, gy), xytext=(1.5, 3.5),
                arrowprops=dict(arrowstyle='->', color=NAVY, lw=1.2, connectionstyle='arc3,rad=0'))

# Gateway A -> Ethereum
ax.annotate('', xy=(5.2, 5.3), xytext=(4.4, 5.6), arrowprops=arrow_kw)
# Ethereum -> Surface A
ax.annotate('', xy=(7.5, 5.3), xytext=(6.8, 5.3), arrowprops=arrow_kw)

# Gateway B -> Ethereum
ax.annotate('', xy=(5.2, 3.55), xytext=(4.4, 3.65), arrowprops=arrow_kw)
# Ethereum -> Surface B
ax.annotate('', xy=(7.5, 3.55), xytext=(6.8, 3.55), arrowprops=arrow_kw)

# Gateway B -> Tron
ax.annotate('', xy=(5.2, 3.0), xytext=(4.4, 3.35), arrowprops=arrow_kw)
# Tron -> Surface B2
ax.annotate('', xy=(7.5, 3.0), xytext=(6.8, 3.0), arrowprops=arrow_kw)

# Gateway C -> Ethereum
ax.annotate('', xy=(5.2, 1.15), xytext=(4.4, 1.4), arrowprops=arrow_kw)
# Ethereum -> Surface C
ax.annotate('', xy=(7.5, 1.15), xytext=(6.8, 1.15), arrowprops=arrow_kw)

# ── Caption ──
fig.text(0.5, -0.02,
         'The same dollar token inherits different compliance, monetary, and safe-haven properties\n'
         'depending on which gateway routes it and which blockchain it traverses.',
         ha='center', fontsize=10, fontstyle='italic', color='#555555')

fig.text(0.02, -0.06, "Source: Author's framework.", fontsize=8, fontstyle='italic', color='#888888')

# ── Tier legend ──
legend_elements = [
    mpatches.Patch(facecolor=NAVY, edgecolor=NAVY, alpha=0.9, label='Tier 1 (CLII > 0.75)'),
    mpatches.Patch(facecolor=BLUE, edgecolor=BLUE, alpha=0.9, label='Tier 2 (CLII 0.30-0.75)'),
    mpatches.Patch(facecolor=LIGHT, edgecolor=GRAY, label='Tier 3 (CLII < 0.30)'),
]
ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(0.0, 1.0),
          fontsize=9, framealpha=0.9, edgecolor='#CCCCCC', fancybox=True)

fig.tight_layout()
out = MEDIA / 'exhibit_conceptual_schematic.png'
fig.savefig(out, dpi=300, bbox_inches='tight', facecolor='white')
plt.close(fig)
print(f'Saved: {out}')
