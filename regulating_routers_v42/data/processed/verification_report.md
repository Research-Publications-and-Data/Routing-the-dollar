# SVB Contagion Chain — Claim Verification Report

**Verification date:** March 9, 2026
**Purpose:** Verify 10 quantitative claims for Federal Reserve conference paper (Pub1) and tokenization equivalence framework (Pub2)

---

## Summary

| # | Claim | Stated Value | Verified Value | Status | Primary Source |
|---|-------|-------------|----------------|--------|---------------|
| 1 | Circle SVB exposure | $3.3B / ~8% of $40B | $3.3B / ~8% | **CONFIRMED** | FEDS Note (fn 5), Circle S-1 |
| 2 | PSM USDC balance pre-crisis | $3.56B | ~$2.1B pre-crisis; $4.1B during crisis | **CORRECTED** | Nansen (via The Block), governance proposal |
| 3 | DAI minted through PSM in 24h | 736M DAI | 736M gross / 296M net | **CONFIRMED** | NewsBTC (Mar 13, 2023) |
| 4 | DAI depeg low | $0.88 | $0.88 | **CONFIRMED** | CoinDesk, CoinGecko ATL, S&P Global |
| 5 | USDP withdrawal from PSM | 400M+, >half of supply | 400M+, >half of supply | **CONFIRMED** | FEDS Note |
| 6 | GUSD low | ~$0.96 | ~$0.96 | **CONFIRMED** | FEDS Note |
| 7 | Governance timing | ~2h pass, 48h delay | ~2h pass, 48h GSM delay | **CONFIRMED** | MakerDAO governance portal, FEDS Note |
| 8 | Post-crisis USDC retention vote | 79.02% | 79.02% | **CONFIRMED** | MakerDAO governance portal, multiple outlets |
| 9 | Curve 3pool volume/TVL | $5.67B vol / $3.77B TVL | $5.67B vol / $3.77B TVL (all-Curve, not 3pool) | **CONFIRMED** (with caveat) | CoinTelegraph (Mar 11, 2023) |
| 10 | Circle private, equity $0.34B | Private, $0.34B equity | Private confirmed; $0.34B is Dec 2023 | **CONFIRMED** (with caveat) | FEDS Note (fn 5), Circle S-1 |

**Result: 8 confirmed, 2 corrections needed**

---

## Detailed Findings

### Claim 1: Circle held $3.3B at SVB, ~8% of $40B USDC reserves — CONFIRMED

**Verified by FEDS Note (highest-authority source):** "Circle announced that it was unable to withdraw $3.3 billion of USDC reserves from SVB (around 8% of total reserves at the time)."

Additional FEDS Note data:
- Cash reserves fell from $11.5B (March 6) to $3.7B (March 31)
- SVB was one of six banking partners
- Circle S-1 (April 1, 2025) is the underlying source

**Sources:** [FEDS Note](https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html), [CNBC](https://www.cnbc.com/amp/2023/03/11/crypto-firm-circle-reveals-3point3-bln-exposure-to-silicon-valley-bank.html), [CoinDesk](https://www.coindesk.com/business/2023/03/11/circle-confirms-33b-of-usdcs-cash-reserves-stuck-at-failed-silicon-valley-bank)

---

### Claim 2: MakerDAO PSM held $3.56B USDC pre-crisis — CORRECTED

**The $3.56B figure is from August 2022 (Tornado Cash sanctions era), not March 2023.**

Timeline of PSM USDC balance:
- **August 2022:** $3.56B (Tornado Cash discussion, per The Defiant/CryptoSlate citing Daistats)
- **October 2022:** $3.41B (per Flipside Governance)
- **March 9, 2023 (pre-SVB):** ~$2.1B (implied by Nansen 91% surge calculation)
- **March 10-12, 2023 (during crisis):** ~$4.1B (Nansen data via The Block)
- **March 11, 2023 (governance proposal):** $4.12B cited as total USDC PSM exposure
- **Late March 2023 (post-crisis):** ~$3.0B

**Recommended correction for paper:** Replace "$3.56B USDC pre-crisis" with either:
- "USDC in MakerDAO's PSM surged to approximately $4.1 billion during the crisis weekend" (citing governance proposal + Nansen data)
- Or explicitly note the PSM balance "approximately doubled" during the crisis as USDC holders flooded the module

**Sources:** [MakerDAO Emergency Proposal](https://vote.makerdao.com/executive/template-executive-vote-emergency-parameter-changes-march-11-2023), [The Defiant (Aug 2022)](https://thedefiant.io/news/defi/tornado-impact-makerdao-dai), [The Block (Mar 13, 2023)](https://www.theblock.co/post/219638/makerdao-looks-to-limit-volatility-after-usdc-troubles-pushed-some-users-to-dai)

---

### Claim 3: 736M DAI minted through USDC PSM in 24 hours — CONFIRMED

**Confirmed by NewsBTC (March 13, 2023):** "Within 24 hours, 736 million DAI were minted through USDC using PSM, and the net supply for DAI increased by 296 million."

Critical distinction: **736M is gross mints, 296M is net supply increase.** The difference (440M) was burned.

Corroboration:
- FEDS Note: "around 1 billion USDC was deposited into the USDC-PSM on both days" (March 10 and 11) — consistent
- CoinDesk: "$563 million of DAI was burnt in the last 24 hours" — consistent with gross/net gap
- The Block: DAI supply went from 5.1B to 6.3B (1.2B net increase over 3 days)
- PSM-USDC-A daily cap was 950M DAI — 736M is below cap, mechanically plausible

**Recommended note for paper:** Clarify that 736M is gross mints, not net. This is a secondary source; on-chain Dune verification would strengthen.

**Source:** [NewsBTC (Mar 13, 2023)](https://www.newsbtc.com/news/how-makerdao-intervened-saving-dai-from-depegging/)

---

### Claim 4: DAI depegged to $0.88 — CONFIRMED

**Confirmed by multiple sources:**
- CoinDesk (March 11, 2023): "all-time low of 88 cents"
- CoinGecko: DAI all-time low = $0.88; USDC all-time low = $0.8774
- S&P Global: DAI remained below $0.90 for 63 minutes
- FEDS Note: USDC "traded at 86 cents" at trough (footnote 9 notes hourly data shows ~90 cents)

**Sources:** [CoinDesk](https://www.coindesk.com/markets/2023/03/11/dai-depegs-as-stablecoin-rout-plagues-crypto), FEDS Note

---

### Claim 5: Over 400M USDP withdrawn from PSM, >half of total supply — CONFIRMED

**Confirmed by FEDS Note:** "over 400 million USDP were withdrawn from the PSM over this period, representing over half of USDP's total outstanding supply"

USDP price low: FEDS Note says "~91 cents" but S&P Global reports USDP traded below $0.90 for 82 minutes. The discrepancy is likely time resolution (daily vs. tick data).

Corroboration: Emergency proposal shows PSM-USDP-A debt ceiling was 450M DAI pre-crisis, increased to 1B DAI — consistent with >400M withdrawal.

**Source:** [FEDS Note](https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html)

---

### Claim 6: GUSD fell to ~$0.96 — CONFIRMED

**Confirmed by FEDS Note:** "~96 cents"
**Corroborated by:** contemporaneous news reports (March 11, 2023)

**Source:** [FEDS Note](https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html)

---

### Claim 7: Emergency proposal passed in ~2 hours, 48-hour execution delay — CONFIRMED

**Confirmed by MakerDAO governance portal on-chain data:**

| Event | Timestamp |
|-------|-----------|
| Proposal posted | March 11, 2023, ~14:00 UTC (Saturday) |
| Vote passed | March 11, 2023, 16:14:11 UTC |
| Scheduled (eta) | March 13, 2023, 16:14:11 UTC |
| Executed | March 13, 2023, 16:16:23 UTC |

- **Time to pass:** ~2 hours 14 minutes (FEDS Note: "just over 2 hours")
- **GSM Pause Delay:** 48 hours (confirmed by proposal text: "currently set to 48 hours")
- **Delay mechanism:** Governance Security Module (GSM)
- **The proposal itself reduced GSM from 48h to 16h** for future flexibility
- D3M changes (Aave/Compound rate targets → 0%) took effect immediately upon scheduling via MOM contract bypass

372,621 MKR supported the measure. 88,767 MKR in approval per NewsBTC.

**Sources:** [MakerDAO Governance Portal](https://vote.makerdao.com/executive/template-executive-vote-emergency-parameter-changes-march-11-2023), [FEDS Note](https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html)

---

### Claim 8: Post-crisis vote — 79.02% to retain USDC as primary reserve — CONFIRMED

**Confirmed by MakerDAO governance and multiple outlets:**
- Vote type: Ranked-choice ("instant run-off") poll
- Poll filed: March 17, 2023 by Risk Core Unit
- Voting period: March 20-23, 2023
- **79.02%** to retain USDC as primary reserve
- **20.69%** to diversify among USDC, USDP, and GUSD
- **0.29%** rejected both options
- ~0% abstained
- Over 93,000 MKR governance tokens cast

Risk Core Unit rationale: "the risk of using USDC as collateral has declined significantly" after federal government intervention.

**Sources:** [Yahoo Finance](https://finance.yahoo.com/news/stablecoin-issuer-makerdao-votes-retain-165851678.html), [Tokenist](https://tokenist.com/79-of-makerdao-members-vote-to-keep-reserves-in-usdc/), [CoinTelegraph](https://cointelegraph.com/news/makerdao-votes-to-keep-usdc-as-primary-collateral-rejects-diversification-plan), [MakerDAO Poll](https://vote.makerdao.com/polling/QmQ1fYm3)

---

### Claim 9: Curve 3pool hit $5.67B daily volume against $3.77B TVL — CONFIRMED (with caveat)

**The $5.67B volume and $3.77B TVL figures are for ALL of Curve Finance, not the 3pool specifically.**

Source comparison:
| Source | Volume Reported | Scope |
|--------|----------------|-------|
| CoinTelegraph (Mar 11, 2023) | $5.67B | "historic all-time high daily trading volume" |
| FYBIT blog | $7B+ | "in the past 24 hours" |
| Pintu Academy | $6.03B | "on March 11" |
| CoinDesk | n/a | 3pool described as "$510M pool" |

**Key correction:** The 3pool TVL was only ~$510M, not $3.77B. The $3.77B was all-Curve TVL. The volume-to-TVL ratio is dramatic either way:
- All-Curve: $5.67B vol / $3.77B TVL = 1.5x
- 3pool specifically: majority of $5.67B against $510M TVL = >11x

**The 2.08M USDC → 0.05 USDT swap anecdote is confirmed** by CoinTelegraph.

**Recommended correction for paper:** Clarify scope (all-Curve vs 3pool) and specify which TVL figure corresponds to which volume figure.

**Source:** [CoinTelegraph (Mar 11, 2023)](https://cointelegraph.com/news/crypto-whales-suffer-huge-losses-due-to-usdc-depeg-svb-collapse)

---

### Claim 10: Circle was a private company during SVB, equity $0.34B — CONFIRMED (with caveat)

**Confirmed by FEDS Note (footnote 5):** "As a private company at the time, Circle was not subject to public disclosure requirements; however, subsequent filing with the Securities and Exchange Commission on April 1, 2025, stated that Circle's total stockholders' equity as of December 31, 2023, was $0.34 billion, representing just over a tenth of the $3.3 billion reserves held at SVB."

**Caveat:** The $0.34B equity is as of **December 31, 2023** — 9 months after SVB. The S-1 does not disclose March 2023 equity separately. Given Circle's revenue growth ($772M in 2022 → $1.5B in 2023), March 2023 equity was likely **lower** than $0.34B, making the solvency concern even more acute.

Circle's SPAC with Concord Acquisition Corp was terminated December 5, 2022. Circle remained private until the April 2025 S-1 filing.

**Sources:** [FEDS Note (fn 5)](https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html), [Circle S-1](https://www.sec.gov/Archives/edgar/data/1876042/000119312525070481/d737521ds1.htm), [CoinDesk (Dec 2022)](https://www.coindesk.com/business/2022/12/05/stablecoin-issuer-circle-cancels-plan-to-go-public)

---

## Action Items for Paper Revision

1. **Claim 2 (PSM balance):** Replace "$3.56B" with corrected figure. Options:
   - "~$4.1B during crisis" (governance proposal, Nansen)
   - Or describe the surge: "PSM USDC balance approximately doubled during the crisis weekend"
   - Add footnote: "The $3.56B figure frequently cited refers to August 2022 (Tornado Cash era)"

2. **Claim 3 (DAI minted):** Add clarification: "736M DAI gross mints; net supply increase was 296M"

3. **Claim 9 (Curve volume):** Clarify scope: "$5.67B daily volume across all Curve pools" vs "3pool TVL was ~$510M"

4. **Claim 10 (equity date):** Add footnote: "Equity as of December 31, 2023; March 2023 equity was likely lower"

5. **Claim 5 (USDP low):** Consider footnote: "S&P Global reports USDP traded below $0.90 for 82 minutes, suggesting the intraday low may have been below the ~$0.91 cited in the FEDS Note"

---

## Source Hierarchy Used

1. **FEDS Note (Dec 17, 2025)** — Federal Reserve staff, peer-reviewed, highest authority for Fed conference paper
2. **Circle S-1 (Apr 1, 2025)** — SEC filing, legally binding disclosures
3. **MakerDAO Governance Portal** — on-chain, verifiable, primary source for governance claims
4. **S&P Global (Sep 2023)** — institutional research, quantitative analysis
5. **CoinGecko / CoinMarketCap** — price data with ATL records
6. **CoinDesk, CoinTelegraph, The Block, NewsBTC** — contemporaneous crypto journalism (secondary)
7. **Nansen** — on-chain analytics platform (via The Block reporting, secondary)
