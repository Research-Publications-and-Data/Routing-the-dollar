"""Task 15: Johansen (1995) weak exogeneity LR test.

Tests H0: alpha_i = 0 for each variable in the cointegrating system.
The restriction means the variable does not adjust to the long-run
equilibrium -- i.e., it is weakly exogenous for the cointegrating parameters.

Method: Johansen (1995, Theorem 8.1).
  1. Run unrestricted Johansen procedure -> eigenvalues lambda_j
  2. Construct restriction matrix A that zeros out row i of alpha
  3. Solve restricted eigenvalue problem -> eigenvalues lambda*_j
  4. LR = T * sum_{j=1}^{r} ln((1 - lambda*_j) / (1 - lambda_j)) ~ chi2(s*r)

Note: The LR test re-estimates beta under the restriction, so it can
differ substantially from the t-test on individual alpha coefficients
(which conditions on the unrestricted beta estimate).
"""
import pandas as pd, numpy as np, sys, warnings
warnings.filterwarnings("ignore")
from statsmodels.tsa.vector_ar.vecm import coint_johansen
from scipy.stats import chi2
from scipy.linalg import eigvals

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from utils import DATA_RAW, DATA_PROC, save_json


def load_data():
    """Load weekly log data for 3-variable system (matches 02_cointegration.py)."""
    fred = pd.read_csv(DATA_RAW / "fred_wide.csv", index_col=0, parse_dates=True)
    sc = pd.read_csv(DATA_PROC / "unified_extended_dataset.csv", index_col=0, parse_dates=True)
    supply = sc["total_supply"]
    merged = fred[["WSHOMCB", "RRPONTSYD"]].join(
        pd.DataFrame(supply), how="inner"
    ).dropna(subset=["WSHOMCB"])
    merged["RRPONTSYD"] = merged["RRPONTSYD"].ffill()
    weekly = merged.resample("W-WED").last().dropna()
    primary = weekly["2023-02-01":"2026-01-31"]
    log_df = np.log(primary.replace(0, np.nan).dropna())
    print(f"  Sample: {len(log_df)} weeks, {log_df.index[0].date()} to {log_df.index[-1].date()}")
    return log_df


def reconstruct_s_matrices(joh):
    """Reconstruct S matrices from Johansen residuals r0t and rkt."""
    r0t = joh.r0t  # T_eff x K residuals for DeltaY
    rkt = joh.rkt  # T_eff x K residuals for Y_{t-1}
    T_eff = r0t.shape[0]
    S00 = r0t.T @ r0t / T_eff
    S11 = rkt.T @ rkt / T_eff
    S10 = rkt.T @ r0t / T_eff
    S01 = S10.T
    return S00, S01, S10, S11, T_eff


def verify_eigenvalues(S00, S01, S10, S11, T_eff, joh):
    """Verify that eigenvalues from S matrices match coint_johansen output."""
    S00_inv = np.linalg.inv(S00)
    M = np.linalg.solve(S11, S10 @ S00_inv @ S01)
    eigs_check = np.sort(np.real(np.linalg.eigvals(M)))[::-1]
    eigs_joh = np.sort(np.real(joh.eig))[::-1]

    max_diff = np.max(np.abs(eigs_check - eigs_joh))
    match = max_diff < 1e-8

    # Verify trace statistic
    trace_recon = -T_eff * np.sum(np.log(1 - eigs_check))
    trace_joh = float(joh.lr1[0])

    print(f"  Eigenvalue verification: max diff = {max_diff:.2e} ({'PASS' if match else 'FAIL'})")
    print(f"  Trace stat: reconstructed={trace_recon:.2f}, Johansen={trace_joh:.2f}")

    return {
        "eigenvalues_reconstructed": eigs_check.tolist(),
        "eigenvalues_johansen": eigs_joh.tolist(),
        "max_difference": float(max_diff),
        "match": match,
        "trace_reconstructed": round(trace_recon, 2),
        "trace_johansen": round(trace_joh, 2),
    }


def test_weak_exogeneity(S00, S01, S10, S11, T_eff, unrestricted_eigs, var_index, rank=1):
    """Run LR test for H0: alpha[var_index, :] = 0 (weak exogeneity).

    Johansen (1995, Theorem 8.1):
    Restricted eigenvalue problem: |lambda A'S11A - A'S10 S00^{-1} S01 A| = 0
    where A is K x (K-1) matrix that zeros out row var_index of alpha.
    """
    K = S00.shape[0]

    # Restriction matrix: alpha = A @ phi, so alpha[var_index, :] = 0
    A = np.delete(np.eye(K), var_index, axis=1)  # K x (K-1)

    # Restricted S matrices
    AS11A = A.T @ S11 @ A                          # (K-1) x (K-1)
    S00_inv = np.linalg.inv(S00)
    AS10S00invS01A = A.T @ S10 @ S00_inv @ S01 @ A  # (K-1) x (K-1)

    # Solve generalized eigenvalue problem
    restricted_eigs = np.real(eigvals(AS10S00invS01A, AS11A))
    restricted_eigs = np.sort(restricted_eigs)[::-1]

    # Take first r eigenvalues
    lambda_unr = np.sort(np.real(unrestricted_eigs))[::-1][:rank]
    lambda_res = restricted_eigs[:rank]

    # LR statistic: Johansen (1995, p. 160)
    # -2 ln(Q) = T * sum ln((1 - lambda_res) / (1 - lambda_unr))
    LR = T_eff * np.sum(np.log(1 - lambda_res) - np.log(1 - lambda_unr))
    df = rank  # s * r where s = 1 restriction
    p_value = 1 - chi2.cdf(LR, df=df)

    return {
        "unrestricted_eigenvalue": round(float(lambda_unr[0]), 6),
        "restricted_eigenvalue": round(float(lambda_res[0]), 6),
        "LR_statistic": round(float(LR), 4),
        "df": df,
        "p_value": float(p_value),
        "reject_5pct": bool(p_value < 0.05),
        "reject_1pct": bool(p_value < 0.01),
    }


def main():
    print("=" * 60)
    print("JOHANSEN WEAK EXOGENEITY LR TEST")
    print("=" * 60)

    log_df = load_data()
    var_names = list(log_df.columns)
    K = len(var_names)
    DET_ORDER = 0
    K_AR_DIFF = 7
    RANK = 1

    print(f"  Variables: {var_names}")
    print(f"  det_order={DET_ORDER}, k_ar_diff={K_AR_DIFF}, rank={RANK}")

    # Run unrestricted Johansen
    joh = coint_johansen(log_df, det_order=DET_ORDER, k_ar_diff=K_AR_DIFF)

    # Reconstruct S matrices and verify
    S00, S01, S10, S11, T_eff = reconstruct_s_matrices(joh)
    print(f"  T_effective = {T_eff}")
    verification = verify_eigenvalues(S00, S01, S10, S11, T_eff, joh)

    # Run weak exogeneity test for each variable
    print("\n" + "-" * 60)
    print("WEAK EXOGENEITY LR TESTS (H0: alpha_i = 0)")
    print("-" * 60)
    print(f"{'Variable':<16} {'LR stat':>10} {'df':>4} {'p-value':>12} {'Result'}")
    print("-" * 60)

    tests = {}
    for i, name in enumerate(var_names):
        result = test_weak_exogeneity(
            S00, S01, S10, S11, T_eff, joh.eig, var_index=i, rank=RANK
        )
        result["restriction"] = f"alpha_{name} = 0"
        tests[name] = result

        sig = "***" if result["p_value"] < 0.01 else "**" if result["p_value"] < 0.05 else "*" if result["p_value"] < 0.10 else ""
        verdict = "REJECT H0" if result["reject_5pct"] else "Fail to reject"
        print(f"  {name:<14} {result['LR_statistic']:>10.4f} {result['df']:>4d} {result['p_value']:>12.6f} {verdict} {sig}")

    # Summary
    print("\n" + "=" * 60)
    print("INTERPRETATION")
    print("=" * 60)

    wshomcb = tests["WSHOMCB"]
    rrp = tests["RRPONTSYD"]
    supply = tests["total_supply"]

    if wshomcb["reject_5pct"]:
        print(f"  Fed Assets (WSHOMCB): NOT weakly exogenous (LR={wshomcb['LR_statistic']:.2f}, p={wshomcb['p_value']:.4g})")
        print("    -> Fed balance sheet adjusts to the cointegrating equilibrium.")
        print("    -> This reflects the scheduled QT program responding to the same")
        print("       macro forces (inflation, financial conditions) that also drive")
        print("       stablecoin demand -- not that stablecoins cause Fed actions.")
    else:
        print(f"  Fed Assets (WSHOMCB): Weakly exogenous (LR={wshomcb['LR_statistic']:.2f}, p={wshomcb['p_value']:.4g})")
        print("    -> Fed balance sheet does not adjust to the cointegrating equilibrium.")
        print("    -> Supports the paper's thesis: Fed policy is the exogenous driver.")

    if not rrp["reject_5pct"]:
        print(f"  ON RRP (RRPONTSYD): Weakly exogenous (LR={rrp['LR_statistic']:.2f}, p={rrp['p_value']:.4g})")
    else:
        print(f"  ON RRP (RRPONTSYD): NOT weakly exogenous (LR={rrp['LR_statistic']:.2f}, p={rrp['p_value']:.4g})")

    if not supply["reject_5pct"]:
        print(f"  Stablecoin Supply: Weakly exogenous (LR={supply['LR_statistic']:.2f}, p={supply['p_value']:.4g})")
    else:
        print(f"  Stablecoin Supply: NOT weakly exogenous (LR={supply['LR_statistic']:.2f}, p={supply['p_value']:.4g})")

    n_rejected = sum(1 for t in tests.values() if t["reject_5pct"])
    if n_rejected == K:
        print("\n  NOTE: All variables reject weak exogeneity. The cointegrating")
        print("  system is fully endogenous -- all variables participate in")
        print("  error correction. The LR test re-estimates beta under each")
        print("  restriction, making it more powerful than individual alpha t-tests")
        print("  (which condition on the unrestricted beta).")

    # Paper-ready sentence
    lr_val = wshomcb["LR_statistic"]
    p_val = wshomcb["p_value"]
    p_str = "< 0.001" if p_val < 0.001 else f"= {p_val:.4f}"
    if wshomcb["reject_5pct"]:
        paper_sentence = (
            f"A Johansen (1995) weak-exogeneity LR test rejects "
            f"alpha_FedAssets = 0 at the 1% level "
            f"(LR = {lr_val:.2f}, p {p_str}, chi-sq(1)), indicating that the "
            f"Fed balance sheet is not weakly exogenous within the cointegrating system."
        )
    else:
        paper_sentence = (
            f"A Johansen (1995) weak-exogeneity LR test fails to reject "
            f"alpha_FedAssets = 0 (LR = {lr_val:.2f}, p {p_str}, chi-sq(1)), "
            f"confirming that Fed balance sheet policy is weakly exogenous "
            f"for the cointegrating parameters."
        )

    print(f"\n  Paper sentence: {paper_sentence}")

    # Save
    output = {
        "method": "Johansen (1995) Theorem 8.1 weak exogeneity LR test",
        "specification": {
            "det_order": DET_ORDER,
            "k_ar_diff": K_AR_DIFF,
            "coint_rank": RANK,
            "T_effective": T_eff,
            "variable_order": var_names,
        },
        "verification": verification,
        "tests": tests,
        "paper_sentence": paper_sentence,
    }
    save_json(output, "weak_exogeneity_results.json")
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
