"""Task C3: Persistence Profile — Cointegrating Equilibrium Half-Life.

Computes the Pesaran & Shin (1996) persistence profile measuring how quickly
the cointegrating equilibrium is restored after a system-wide shock. Outputs
exhibit_c3_persistence_profile.png and persistence_profile.json.
"""
import pandas as pd, numpy as np, matplotlib.pyplot as plt, json, sys, warnings
warnings.filterwarnings("ignore")

from statsmodels.tsa.vector_ar.vecm import VECM
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_RAW, DATA_PROC, EXHIBITS, save_json, save_exhibit, setup_plot_style, color


def load_data():
    """Load weekly log data for VECM estimation."""
    fred = pd.read_csv(DATA_RAW / "fred_wide.csv", index_col=0, parse_dates=True)
    try:
        sc = pd.read_csv(DATA_PROC / "unified_extended_dataset.csv", index_col=0, parse_dates=True)
        supply = sc["total_supply"]
    except FileNotFoundError:
        print("  Pulling stablecoin supply from DefiLlama...")
        import requests
        resp = requests.get("https://stablecoins.llama.fi/stablecoincharts/all?stablecoin=1", timeout=30)
        usdt = [(pd.to_datetime(d["date"], unit="s"), d.get("totalCirculating", {}).get("peggedUSD", 0)) for d in resp.json()]
        resp2 = requests.get("https://stablecoins.llama.fi/stablecoincharts/all?stablecoin=2", timeout=30)
        usdc = [(pd.to_datetime(d["date"], unit="s"), d.get("totalCirculating", {}).get("peggedUSD", 0)) for d in resp2.json()]
        usdt_s = pd.Series(dict(usdt), name="usdt")
        usdc_s = pd.Series(dict(usdc), name="usdc")
        supply = usdt_s + usdc_s.reindex(usdt_s.index, fill_value=0)
        supply.name = "total_supply"

    merged = fred[["WSHOMCB", "RRPONTSYD"]].join(pd.DataFrame(supply), how="inner").dropna(subset=["WSHOMCB"])
    merged["RRPONTSYD"] = merged["RRPONTSYD"].ffill()
    weekly = merged.resample("W-WED").last().dropna()
    primary = weekly["2023-02-01":"2026-01-31"]
    print(f"  Primary sample: {len(primary)} weeks, {primary.index[0].date()} to {primary.index[-1].date()}")
    return primary


def get_var_level_matrices(result):
    """Extract VAR(p) in levels coefficient matrices from VECM result.

    Uses statsmodels' built-in var_rep property which returns the
    VAR(p) representation as an (p, n_vars, n_vars) array.
    """
    return [result.var_rep[i] for i in range(result.var_rep.shape[0])]


def compute_ma_coefficients(A_matrices, n_vars, H):
    """Compute MA representation coefficients C(h) recursively.

    C(0) = I
    C(h) = sum_{i=1}^{min(h,p)} A_i @ C(h-i)
    """
    p = len(A_matrices)
    C = [np.eye(n_vars)]  # C(0) = I
    for h in range(1, H + 1):
        C_h = np.zeros((n_vars, n_vars))
        for i in range(1, min(h, p) + 1):
            C_h += A_matrices[i - 1] @ C[h - i]
        C.append(C_h)
    return C


def compute_persistence_profile(beta, C, sigma, H):
    """Compute Pesaran & Shin (1996) persistence profile.

    psi(h) = beta' C(h) Sigma beta / (beta' Sigma beta)
    """
    beta_sigma_beta = float((beta.T @ sigma @ beta).item())
    profile = []
    for h in range(H + 1):
        numerator = float((beta.T @ C[h] @ sigma @ beta).item())
        profile.append(numerator / beta_sigma_beta)
    return profile


def bootstrap_persistence_profiles(log_df, k_ar_diff, coint_rank, H, n_boot=500):
    """Bootstrap confidence intervals for the persistence profile."""
    n_vars = log_df.shape[1]
    profiles = []

    # Fit base model to get residuals
    base_model = VECM(log_df, k_ar_diff=k_ar_diff, coint_rank=coint_rank, deterministic='n')
    base_result = base_model.fit()
    resids = base_result.resid
    fitted = log_df.values[k_ar_diff + 1:] - resids  # approximate fitted values

    np.random.seed(42)
    success = 0
    for b in range(n_boot * 3):  # allow extra attempts for failures
        if success >= n_boot:
            break
        try:
            # Resample residuals
            idx = np.random.choice(len(resids), size=len(resids), replace=True)
            boot_resids = resids[idx]
            boot_y = fitted + boot_resids
            boot_df = pd.DataFrame(boot_y, columns=log_df.columns)

            # Re-estimate VECM
            boot_vecm = VECM(boot_df, k_ar_diff=k_ar_diff, coint_rank=coint_rank, deterministic='n')
            boot_result = boot_vecm.fit()

            beta_b = boot_result.beta[:, 0:1]
            sigma_b = boot_result.sigma_u
            A_b = get_var_level_matrices(boot_result)
            C_b = compute_ma_coefficients(A_b, n_vars, H)
            prof = compute_persistence_profile(beta_b, C_b, sigma_b, H)

            # Sanity: profile should start near 1 and generally decrease
            if 0.8 < prof[0] < 1.2 and not any(np.isnan(prof)):
                profiles.append(prof)
                success += 1
        except Exception:
            continue

    if success < 50:
        print(f"  WARNING: Only {success} bootstrap replications succeeded")
        return None, None

    profiles = np.array(profiles)
    ci_5 = np.percentile(profiles, 5, axis=0).tolist()
    ci_95 = np.percentile(profiles, 95, axis=0).tolist()
    print(f"  Bootstrap: {success} successful replications")
    return ci_5, ci_95


def main():
    print("=" * 60)
    print("PERSISTENCE PROFILE (Pesaran & Shin 1996)")
    print("=" * 60)

    # Load data
    df = load_data()
    log_df = np.log(df.replace(0, np.nan).dropna())
    n_vars = log_df.shape[1]
    var_names = list(log_df.columns)
    T = len(log_df)
    print(f"  Variables: {var_names}")
    print(f"  T = {T} weeks")

    # VECM estimation (matching paper specification)
    k_ar_diff = 7  # lag 8 AIC-optimal, so k_ar_diff = 7
    coint_rank = 1
    H = 52  # 1-year horizon

    print(f"\nEstimating VECM (k_ar_diff={k_ar_diff}, rank={coint_rank})...")
    model = VECM(log_df, k_ar_diff=k_ar_diff, coint_rank=coint_rank, deterministic='n')
    result = model.fit()

    # Extract parameters
    beta = result.beta[:, 0:1]  # (3x1) cointegrating vector
    alpha = result.alpha[:, 0:1]  # (3x1) adjustment speeds
    sigma = result.sigma_u  # (3x3) innovation covariance

    print(f"\n  beta  = {beta.flatten()}")
    print(f"  alpha = {alpha.flatten()}")
    print(f"  sigma =\n{sigma}")

    # Convert to VAR in levels and compute MA coefficients
    A_matrices = get_var_level_matrices(result)
    C = compute_ma_coefficients(A_matrices, n_vars, H)

    # Compute persistence profile
    profile = compute_persistence_profile(beta, C, sigma, H)
    print(f"\n  Profile (first 15 weeks):")
    for h in range(min(15, H + 1)):
        print(f"    h={h:2d}: psi={profile[h]:.4f}")

    # Find half-life
    half_life = None
    for h in range(H + 1):
        if profile[h] < 0.50:
            half_life = h
            break
    if half_life is None:
        # If doesn't cross 0.5 within horizon, extrapolate
        half_life = H
        print(f"\n  WARNING: Profile does not cross 0.50 within {H} weeks")
    else:
        print(f"\n  Half-life: {half_life} weeks")

    quarter_absorption = 1.0 - profile[min(13, H)]
    year_absorption = 1.0 - profile[H]
    print(f"  Quarter absorption (13 wks): {quarter_absorption:.1%}")
    print(f"  Year absorption (52 wks): {year_absorption:.1%}")

    # Bootstrap CIs
    print(f"\nBootstrapping ({500} replications)...")
    ci_5, ci_95 = bootstrap_persistence_profiles(log_df, k_ar_diff, coint_rank, H, n_boot=500)

    # Compute smoothed half-life for JSON
    profile_arr = np.array(profile)
    window = 8
    smoothed_arr = np.convolve(profile_arr, np.ones(window) / window, mode='valid')
    smooth_x_arr = list(range(window // 2, window // 2 + len(smoothed_arr)))
    smoothed_hl = None
    for i, v in enumerate(smoothed_arr):
        if v < 0.50:
            smoothed_hl = smooth_x_arr[i]
            break
    if smoothed_hl is None:
        smoothed_hl = H

    smooth_q13_idx = min(13 - window // 2, len(smoothed_arr) - 1)
    smooth_quarter_abs = 1.0 - float(smoothed_arr[smooth_q13_idx]) if smooth_q13_idx >= 0 else quarter_absorption

    # Save JSON
    output = {
        "half_life_weeks": int(half_life),
        "half_life_weeks_smoothed": int(smoothed_hl),
        "profile": [round(p, 6) for p in profile],
        "quarter_absorption": round(quarter_absorption, 4),
        "quarter_absorption_smoothed": round(smooth_quarter_abs, 4),
        "year_absorption": round(year_absorption, 4),
        "bootstrap_ci_5": [round(x, 6) for x in ci_5] if ci_5 else None,
        "bootstrap_ci_95": [round(x, 6) for x in ci_95] if ci_95 else None,
        "vecm_params": {
            "alpha": [round(float(a), 6) for a in alpha.flatten()],
            "beta": [round(float(b), 6) for b in beta.flatten()],
            "lag": k_ar_diff + 1,
            "k_ar_diff": k_ar_diff,
            "rank": coint_rank,
            "T": T,
        }
    }
    save_json(output, "persistence_profile.json")

    # Plot
    setup_plot_style()
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.subplots_adjust(bottom=0.15, right=0.72)

    weeks = list(range(H + 1))

    # Bootstrap CI band (clip to 0 for cleaner display)
    if ci_5 and ci_95:
        ci_5_clipped = [max(0, v) for v in ci_5]
        ci_95_clipped = [max(0, v) for v in ci_95]
        ax.fill_between(weeks, ci_5_clipped, ci_95_clipped, color="#003366", alpha=0.15,
                        label="90% CI")

    # Main profile line (raw, clipped to 0)
    profile_clipped = [max(0, v) for v in profile]
    ax.plot(weeks, profile_clipped, color=color("primary"), linewidth=1, alpha=0.5,
            label=r"Raw $\psi(h)$", zorder=4)

    # Smoothed profile (8-week centered moving average)
    profile_arr = np.array(profile)
    window = 8
    smoothed = np.convolve(profile_arr, np.ones(window) / window, mode='valid')
    smooth_x = list(range(window // 2, window // 2 + len(smoothed)))
    smoothed_clipped = np.clip(smoothed, 0, None)
    ax.plot(smooth_x, smoothed_clipped, color=color("primary"), linewidth=2.5,
            label=f"Smoothed ({window}w MA)", zorder=6)

    # Half-life reference lines (use smoothed half-life)
    smooth_hl = None
    for i, v in enumerate(smoothed):
        if v < 0.50:
            smooth_hl = smooth_x[i]
            break

    ax.axhline(0.50, color=color("stress"), linewidth=1, linestyle="--", alpha=0.7)
    hl_display = smooth_hl if smooth_hl is not None else half_life
    if hl_display < H:
        ax.axvline(hl_display, color=color("stress"), linewidth=1, linestyle="--", alpha=0.7)
        ax.annotate(f"Half-life: {hl_display} weeks",
                    xy=(hl_display, 0.50), xytext=(hl_display + 10, 0.88),
                    fontsize=10, fontweight="bold", color=color("stress"),
                    arrowprops=dict(arrowstyle="->", color=color("stress"), lw=1.5),
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                              edgecolor=color("stress"), alpha=0.95))

    # Text annotation box — outside chart to the right
    q13_val = profile[min(13, H)]
    smooth_q13 = float(smoothed[min(13 - window // 2, len(smoothed) - 1)]) if len(smoothed) > 0 else q13_val
    smooth_qa = 1.0 - smooth_q13
    textstr = (f"Unit shock → {smooth_qa:.0%} absorbed\n"
               f"within 13 weeks (one quarter);\n"
               f"smoothed half-life: {hl_display} weeks")
    props = dict(boxstyle="round,pad=0.5", facecolor="#F5F5F5", edgecolor="#CCCCCC", alpha=0.95)
    ax.text(1.02, 0.15, textstr, transform=ax.transAxes, fontsize=8.5,
            verticalalignment="top", horizontalalignment="left", bbox=props)

    ax.set_xlabel("Horizon (weeks)")
    ax.set_ylabel(r"Fraction of Disequilibrium Remaining  $\psi(h)$")
    ax.set_title("Persistence Profile: Cointegrating Equilibrium Adjustment")
    ax.set_xlim(0, H)
    ax.set_ylim(0, 1.05)
    ax.legend(loc="upper left", bbox_to_anchor=(0.01, 0.99), fontsize=8, framealpha=0.9)

    save_exhibit(fig, "exhibit_c3_persistence_profile.png",
                 f"Source: Authors' VECM estimation (lag {k_ar_diff+1}, rank {coint_rank}, T = {T} weeks). "
                 "Persistence profile computed following Pesaran and Shin (1996). Bootstrap CI: 500 replications.")

    print("\n" + "=" * 60)
    print(f"RESULT: Half-life = {half_life} weeks")
    print(f"  13-week absorption: {quarter_absorption:.1%}")
    print(f"  52-week absorption: {year_absorption:.1%}")
    print("=" * 60)


if __name__ == "__main__":
    main()
