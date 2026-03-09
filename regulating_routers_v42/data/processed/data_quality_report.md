# Data Quality Report: Expanded Gateway Registry v2

## 1. Internal Transfer Audit

**Entities audited:** 4
**Material internal transfers (>5%):** Binance, OKX

| Entity | Gross Volume | Internal Volume | Internal % | Status |
|--------|-------------|----------------|-----------|--------|
| Binance | $2,895.0B | $531.0B | 18.3% | MATERIAL |
| OKX | $268.4B | $29.1B | 10.8% | MATERIAL |
| Kraken | $390.8B | $2.7B | 0.7% | OK |
| Coinbase | $1,899.8B | $0.0B | 0.0% | OK |

**Recommendation:** Report both gross and net figures. Binance internal transfers
(18.3%) reflect wallet consolidation operations, not genuine gateway throughput.

## 2. Double-Counting Check (Bilateral Flows)

**Total bilateral volume:** $21.8B
**As % of gross gateway volume:** 0.3%

**Top bilateral pairs:**

| From | To | Volume | Transfers |
|------|-----|--------|-----------|
| Binance | Tether | $5.8B | 238 |
| Binance | Bybit | $5.6B | 395 |
| Coinbase | OKX | $4.3B | 11,058 |
| Binance | OKX | $2.9B | 4,149 |
| Circle | 1inch | $2.3B | 733 |
| Kraken | OKX | $0.7B | 996 |
| Bybit | OKX | $0.2B | 536 |
| Circle | OKX | $0.1B | 166 |

**Conclusion:** Bilateral flows are only 0.3% of total gateway volume.
Double-counting is negligible and does not materially affect tier share calculations.

## 3. Net Volume Analysis

**Gross total:** $7.743T
**Net total (gross - internal):** $7.180T
**Internal transfer adjustment:** 7.3%

**Net Tier Shares (after removing internal transfers):**

- Tier 1: 46.9%
- Tier 2: 49.8%
- Tier 3: 3.3%

**Recommendation:** Internal transfers are 7.3% of gross volume. Report BOTH gross and net figures in paper. Use net figures for HHI/tier share calculations.

## 4. Gemini Gateway Profile

**USDC/USDT volume:** near-zero (confirmed via daily query)
**GUSD market cap (peak):** $858M
**GUSD market cap (latest):** $45M
**GUSD trend:** declining

**Key Findings:**
- Gemini has near-zero USDC/USDT gateway volume ($21 total in 3 years)
- Gemini's gateway role is limited to GUSD issuance/redemption
- GUSD market cap peaked at ~$858M, now ~$45M (declining 95% from peak)
- Total GUSD transfer volume ~$14B over 3 years, but only $5K through Gemini addresses
- Gemini remains Tier 1 by CLII score but is NOT a material stablecoin gateway
- Original paper's Gemini=23.1% was entirely from Binance address mislabeling
- Recommendation: Keep Gemini in registry for completeness but note immaterial USDC/USDT volume; GUSD role is as issuer not as transfer gateway

## 5. HHI Robustness (Excluding Binance)

| Metric | With Binance | Without Binance |
|--------|-------------|----------------|
| Entity HHI Mean | 2741.9 | 2905.7 |
| Entity HHI Median | 2624.8 | 2723.4 |
| Days > 2,500 | 61.5% | 64.3% |
| Tier HHI Mean | 5020.7 | 5576.9 |

**Interpretation:** Removing Binance increases entity HHI by 164 points. This suggests that Binance moderates concentration by spreading volume.

Removing Binance *increases* entity HHI by ~164 points, confirming that
concentration is structural (driven by Circle+Coinbase dominance in Tier 1),
not merely an artifact of Binance's large volume.

## 6. Address Verification Summary

| Address | Claimed | Verified | Status |
|---------|---------|----------|--------|
| 0x21a31... | Gemini | Binance 36 | CORRECTED (session 1) |
| 0x11111... | 1inch/0x | 1inch AggregationRouterV5 | CONFIRMED |
| 0xE25a3... | Paxos | Paxos Treasury | CONFIRMED (Etherscan) |
| 0xd2440... | Gemini | Gemini | CONFIRMED (near-zero USDC/USDT) |

## 7. Gross vs Net Metrics Comparison

| Metric | Gross | Net (excl. internal) |
|--------|-------|---------------------|
| Tier 1 Share | 40.8% | 46.9% |
| Tier 2 Share | 55.1% | 49.8% |
| Total Volume | $7.743T | $7.180T |
| Entity HHI | 2742 | (recalculate with net) |

---

## Summary for Paper Revision

1. **Internal transfers (7.3% of gross) are material.** Report both gross and net.
   Binance's 18.3% internal rate is wallet consolidation. OKX's 10.8% is similar.
2. **Double-counting (0.3% bilateral) is negligible.** No adjustment needed.
3. **Gemini is confirmed as immaterial** for USDC/USDT. GUSD role is small and declining.
4. **HHI concentration is structural.** Removing Binance increases HHI, not decreases.
5. **Net tier shares: Tier 1 ~47%, Tier 2 ~50%** — more balanced than gross figures suggest.
6. **1inch address confirmed** — not 0x Protocol as originally noted in some references.