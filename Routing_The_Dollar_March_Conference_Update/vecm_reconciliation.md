# VECM Alpha Reconciliation: Table 3 vs. Table 3b

## Summary

Table 3 and Table 3b report **seemingly contradictory** results for ON RRP's adjustment coefficient:

| Source | ON RRP result |
|--------|--------------|
| Table 3 (alpha t-test) | alpha = -0.153, SE = 0.135, t = -1.138, p = 0.255 |
| Table 3b (LR weak exogeneity) | LR = 14.00, df = 1, p < 0.001 |

**Diagnosis: Both tables are correct and from the same specification.** The discrepancy is a well-known methodological phenomenon in VECM estimation, not a coding bug or specification mismatch.

---

## Exact Specification

Both sets of results were produced from the same VECM:

| Parameter | Value |
|-----------|-------|
| Variables | WSHOMCB (Fed assets), RRPONTSYD (ON RRP), total_supply (stablecoin) |
| Frequency | Weekly (Wednesday-to-Wednesday) |
| Sample | 2023-02-01 to 2026-01-28 |
| Observations | 157 weeks (T_effective = 149 after differencing) |
| VAR lag (AIC) | 8 (k_ar_diff = 7) |
| Cointegrating rank | 1 (Johansen trace test) |
| Deterministic | None outside cointegrating relation (det_order = 0) |
| Software | statsmodels VECM + custom Johansen LR implementation |

**Scripts:**
- Table 3 alpha: `scripts/02_cointegration.py` (VECM().fit(), lines 81-106)
- Table 3b LR: `scripts/15_weak_exogeneity.py` (Johansen 1995 Theorem 8.1, lines 82-121)
- Reconciliation: `scripts/vecm_clii_verification.py` (re-runs both from same data)

---

## Full Alpha Vector (Table 3)

| Variable | alpha | SE | t-stat | p-value | Sig. |
|----------|------:|---:|-------:|--------:|------|
| WSHOMCB (Fed Assets) | 0.002713 | 0.000434 | 6.256 | < 0.001 | *** |
| RRPONTSYD (ON RRP) | -0.153319 | 0.134708 | -1.138 | 0.255 | |
| total_supply (Stablecoin) | -0.003547 | 0.002232 | -1.589 | 0.112 | |

**Cointegrating vector (beta):** [1.000, -0.108, -0.627]

---

## Full Weak Exogeneity LR Tests (Table 3b)

| Variable | LR stat | df | p-value | Result |
|----------|--------:|---:|--------:|--------|
| WSHOMCB (Fed Assets) | 15.28 | 1 | < 0.001 | Reject H0 *** |
| RRPONTSYD (ON RRP) | 14.00 | 1 | < 0.001 | Reject H0 *** |
| total_supply (Stablecoin) | 5.38 | 1 | 0.020 | Reject H0 ** |

All three variables reject weak exogeneity: the cointegrating system is fully endogenous.

---

## Explanation of the Discrepancy

The alpha t-test and the Johansen LR test answer different statistical questions using different procedures:

### Alpha t-test (Table 3)
- **Type:** Single-equation Wald-type test
- **Null:** H0: alpha_i = 0
- **Method:** Tests whether the adjustment coefficient is significantly different from zero **conditional on the unrestricted estimate of beta**
- **Inference:** Uses the single equation's variance to compute the standard error

### Johansen LR test (Table 3b)
- **Type:** System-level likelihood ratio test
- **Null:** H0: alpha_i = 0
- **Method:** **Re-estimates beta under the restriction** alpha_i = 0, then compares restricted and unrestricted log-likelihoods
- **Inference:** Exploits cross-equation correlation structure; captures the joint effect of the restriction on both alpha and beta

### Why they diverge for ON RRP

The alpha coefficient for ON RRP (-0.153) is modest relative to its standard error (0.135), producing a marginal t-statistic (-1.14). By itself, this suggests ON RRP may not participate in error correction.

However, when we impose alpha_RRP = 0 and re-estimate the system, the first eigenvalue drops from **0.1471 to 0.0631** -- a **57.1% reduction**. This large eigenvalue shift means the cointegrating relationship deteriorates sharply without ON RRP's participation, producing LR = 14.00 (p < 0.001).

The intuition: ON RRP's error-correction role is imprecisely estimated in a single equation (noisy, hence wide SE), but its removal substantially weakens the system's cointegrating structure. The LR test detects this because it captures how the restriction ripples through all three equations simultaneously.

This is a well-documented phenomenon in the VECM literature. See:
- Johansen (1995), *Likelihood-Based Inference in Cointegrated Vector Autoregressive Models*, Ch. 8
- Juselius (2006), *The Cointegrated VAR Model*, Ch. 8, Section 8.3
- Gonzalo (1994), "Five alternative methods of estimating long-run equilibrium relationships," *Journal of Econometrics* 60: 203-233

---

## Recommended Paper Language

Add as a footnote to Table 3b or as a paragraph immediately following it:

> The equation-level t-statistic for the ON RRP adjustment coefficient (t = -1.14, p = 0.255 in Table 3) and the system-level Johansen LR restriction test (LR = 14.00, p < 0.001 in Table 3b) can differ because the weak exogeneity test is a likelihood ratio test that re-estimates the cointegrating vector beta under the restriction alpha_i = 0, giving it greater statistical power than single-equation inference which conditions on the unrestricted beta (Johansen, 1995, Theorem 8.1). Both results are from the same VECM specification (lag 8, rank 1, 157 weekly observations). The restriction alpha_RRP = 0 reduces the first eigenvalue by 57%, indicating that ON RRP's participation, while imprecisely estimated in isolation, is essential to the system's cointegrating structure.

---

## Verification

Verification script: `scripts/vecm_clii_verification.py`
JSON output: `data/processed/vecm_reconciliation.json`

To reproduce:
```bash
cd Routing_The_Dollar_March_Conference_Update
python scripts/vecm_clii_verification.py
```
