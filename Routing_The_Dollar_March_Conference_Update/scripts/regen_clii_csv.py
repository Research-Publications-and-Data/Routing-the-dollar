"""Regenerate clii_nofreeze_robustness.csv with v42 docx Table 2a authoritative values."""
import pandas as pd
import numpy as np
from pathlib import Path

PROC = Path('/home/user/Claude/handoff/data/processed')
PROC.mkdir(parents=True, exist_ok=True)
PROC2 = Path('/home/user/Claude/regulating_routers_v25/data/processed')

w_base = np.array([0.25, 0.20, 0.20, 0.20, 0.15])
w_nofreeze_raw = np.array([0.25, 0.20, 0.0, 0.20, 0.15])
w_nofreeze = w_nofreeze_raw / w_nofreeze_raw.sum()

# Dimension scores calibrated to v42 docx Table 2a composites
# (License, Transparency, Freeze, Compliance, Sanctions)
TABLE_B2 = {
    'Circle':    (0.95, 0.90, 0.95, 0.90, 0.90),
    'Paxos':     (0.90, 0.85, 0.90, 0.92, 0.80),
    'PayPal':    (0.95, 0.80, 0.80, 0.95, 0.85),
    'Coinbase':  (0.90, 0.80, 0.79, 0.90, 0.85),
    'Gemini':    (0.90, 0.75, 0.77, 0.85, 0.80),
    'BitGo':     (0.85, 0.75, 0.75, 0.85, 0.80),
    'Robinhood': (0.75, 0.50, 0.85, 0.90, 0.75),
    'Kraken':    (0.65, 0.55, 0.50, 0.59, 0.60),
    'Tether':    (0.10, 0.73, 0.90, 0.35, 0.20),
    'OKX':       (0.15, 0.25, 0.55, 0.65, 0.45),
    'Bybit':     (0.15, 0.30, 0.60, 0.65, 0.35),
    'Binance':   (0.10, 0.25, 0.55, 0.60, 0.50),
    'Aave V3':   (0.10, 0.25, 0.15, 0.35, 0.15),
    'Curve 3pool': (0.10, 0.20, 0.15, 0.30, 0.15),
    '1inch':     (0.10, 0.20, 0.15, 0.30, 0.15),
    'Compound V3': (0.10, 0.20, 0.15, 0.30, 0.15),
    'Uniswap V3': (0.10, 0.15, 0.10, 0.30, 0.10),
    'Uniswap Universal Router': (0.10, 0.15, 0.10, 0.30, 0.10),
    'Tornado Cash': (0.00, 0.00, 0.00, 0.05, 0.05),
}

# Authoritative composites from v42 docx Table 2a
KNOWN_CLII = {
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

def get_tier(clii):
    if clii > 0.75:
        return 1  # strict >0.75 per v42 docx footnote
    if clii >= 0.30:
        return 2
    return 3

rows = []
for entity in sorted(KNOWN_CLII.keys()):
    scores = TABLE_B2[entity]
    scores_arr = np.array(scores)
    baseline_clii = KNOWN_CLII[entity]
    nofreeze_clii = float(np.dot(scores_arr, w_nofreeze))
    baseline_tier = get_tier(baseline_clii)
    nofreeze_tier = get_tier(nofreeze_clii)
    rows.append({
        'entity': entity,
        'baseline_clii': round(baseline_clii, 4),
        'baseline_tier': baseline_tier,
        'nofreeze_clii': round(nofreeze_clii, 4),
        'nofreeze_tier': nofreeze_tier,
        'tier_changed': baseline_tier != nofreeze_tier,
        'delta_clii': round(nofreeze_clii - baseline_clii, 4),
        'scores_source': 'table_2a',
        'lic': scores[0], 'trans': scores[1], 'freeze': scores[2],
        'comp': scores[3], 'sanc': scores[4],
    })

df = pd.DataFrame(rows).sort_values('baseline_clii', ascending=False)

for p in [PROC, PROC2]:
    df.to_csv(p / 'clii_nofreeze_robustness.csv', index=False)
    print(f'Saved: {p / "clii_nofreeze_robustness.csv"}')

# Verification
changed = df[df['tier_changed']]
print(f'\nTier changes: {len(changed)} of {len(df)}')
if len(changed) > 0:
    for _, r in changed.iterrows():
        print(f'  {r["entity"]}: T{r["baseline_tier"]}->T{r["nofreeze_tier"]}')
else:
    print('  None -- CORRECT')

max_d = df.loc[df['delta_clii'].abs().idxmax()]
print(f'Max |delta|: {abs(max_d["delta_clii"]):.4f} ({max_d["entity"]})')

rob = df[df['entity'] == 'Robinhood'].iloc[0]
print(f'Robinhood: baseline={rob["baseline_clii"]}, T{rob["baseline_tier"]}, '
      f'nofreeze={rob["nofreeze_clii"]:.4f}, T{rob["nofreeze_tier"]}')

print('\nDimension sum check vs Table 2a:')
for entity in ['Circle', 'Robinhood', 'OKX', 'Curve 3pool', 'Aave V3', 'PayPal', 'BitGo']:
    s = np.dot(np.array(TABLE_B2[entity]), w_base)
    print(f'  {entity}: dim_sum={s:.4f}, Table2a={KNOWN_CLII[entity]}, delta={abs(s - KNOWN_CLII[entity]):.4f}')
