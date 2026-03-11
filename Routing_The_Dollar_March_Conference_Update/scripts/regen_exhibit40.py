"""Regenerate Exhibit 40 (exhibitE1_irf_point.png) with fixed labels.

Fixes:
1. Raw FRED codes → human-readable names (Fed Assets, ON RRP, Stablecoin Supply)
2. Diagonal titles → "own shock" instead of "X -> X"
3. Arrow notation: → instead of ->

Uses cached IRF point estimates from irf_bootstrap_cache.npz.
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────
HANDOFF = Path('/home/user/Claude/handoff')
V25 = Path('/home/user/Claude/Routing_The_Dollar_March_Conference_Update')
CACHE = HANDOFF / 'data' / 'processed' / 'irf_bootstrap_cache.npz'

OUTPUT_DIRS = [
    HANDOFF / 'media',
    HANDOFF / 'exhibits',
    V25 / 'media',
]

# ── Style ────────────────────────────────────────────────────
NAVY = '#1B2A4A'

matplotlib.rcParams.update({
    'font.family': 'serif',
    'font.size': 10,
    'axes.titlesize': 9,
    'axes.titleweight': 'bold',
    'axes.labelsize': 8,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.grid': True,
    'grid.alpha': 0.3,
    'grid.linewidth': 0.5,
})

# ── Load cached IRF ──────────────────────────────────────────
cache = np.load(CACHE)
irf_point = cache['irf_point']  # shape: (27, 3, 3)
print(f"Loaded IRF point estimates: shape {irf_point.shape}")

# ── Variable names (the fix) ─────────────────────────────────
var_names = ['Fed Assets', 'ON RRP', 'Stablecoin Supply']

# ── Generate 3×3 grid ────────────────────────────────────────
fig, axes = plt.subplots(3, 3, figsize=(11, 9))
x = np.arange(irf_point.shape[0])  # 0 to 26

for i in range(3):      # response variable (row)
    for j in range(3):  # shock variable (column)
        ax = axes[i, j]
        ax.plot(x, irf_point[:, i, j], color=NAVY, linewidth=1.8)
        ax.axhline(0, color='gray', linewidth=0.5, linestyle='--')

        # Diagonal = "own shock", off-diagonal = "shock → response"
        if i == j:
            title = f"{var_names[i]} (own shock)"
        else:
            title = f"{var_names[j]} \u2192 {var_names[i]}"
        ax.set_title(title, fontsize=9)

        if i == 2:
            ax.set_xlabel('Weeks', fontsize=8)
        if j == 0:
            ax.set_ylabel('Response', fontsize=8)

fig.suptitle('Impulse Response Functions (26-Week Horizon)',
             fontsize=13, fontweight='bold', y=1.02)
fig.tight_layout(rect=[0, 0.02, 1, 0.98])
fig.text(0.02, 0.01, "Source: FRED, DefiLlama.",
         fontsize=7, fontstyle='italic', color='#666666')

# ── Save ─────────────────────────────────────────────────────
filename = 'exhibitE1_irf_point.png'
for d in OUTPUT_DIRS:
    d.mkdir(parents=True, exist_ok=True)
    outpath = d / filename
    fig.savefig(outpath, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"Saved: {outpath}")
plt.close(fig)

# ── Verification ─────────────────────────────────────────────
print("\n=== VERIFICATION ===")
expected_titles = [
    ("Fed Assets (own shock)",            "[0,0] diagonal"),
    ("ON RRP \u2192 Fed Assets",                  "[0,1] off-diag"),
    ("Stablecoin Supply \u2192 Fed Assets",       "[0,2] off-diag"),
    ("Fed Assets \u2192 ON RRP",                  "[1,0] off-diag"),
    ("ON RRP (own shock)",                "[1,1] diagonal"),
    ("Stablecoin Supply \u2192 ON RRP",           "[1,2] off-diag"),
    ("Fed Assets \u2192 Stablecoin Supply",       "[2,0] off-diag"),
    ("ON RRP \u2192 Stablecoin Supply",           "[2,1] off-diag"),
    ("Stablecoin Supply (own shock)",     "[2,2] diagonal"),
]
for idx, (title, pos) in enumerate(expected_titles):
    i, j = divmod(idx, 3)
    actual = axes[i, j].get_title()
    ok = actual == title
    print(f"  {pos}: '{actual}' {'OK' if ok else 'MISMATCH (expected: ' + title + ')'}")

# No raw codes
all_titles = [axes[i, j].get_title() for i in range(3) for j in range(3)]
has_raw = any(code in t for t in all_titles for code in ['WSHOMCB', 'RRPONTSYD', 'total_supply'])
print(f"\n  No raw FRED codes in titles: {'FAIL' if has_raw else 'OK'}")
diag_own = all('own shock' in axes[i, i].get_title() for i in range(3))
print(f"  All 3 diagonal cells say 'own shock': {'OK' if diag_own else 'FAIL'}")
off_diag_arrow = all('\u2192' in axes[i, j].get_title() for i in range(3) for j in range(3) if i != j)
print(f"  All 6 off-diagonal cells use '\u2192': {'OK' if off_diag_arrow else 'FAIL'}")
print("\nDone.")
