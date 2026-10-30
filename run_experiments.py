#!/usr/bin/env python3
"""
run_experiments.py

CLI entry point. Runs paired randomised baseline-vs-protected trials
across bribery / Sybil / ballot-stuffing attacks, writes CSV + JSON
outputs, runs analysis, and generates all figures + reports.

Usage:
    python run_experiments.py --trials 1000 --seed 42
    python run_experiments.py --attack bribery --trials 1000 --seed 42
    python run_experiments.py --attack all --trials 1000 --seed 42
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

from config import CSV_DIR, JSON_DIR, MC_TRIALS_PER_SCENARIO
from simulation.experiment_runner import run_all_trials
from analysis.comparison import cross_attack_comparison, compare_baseline_protected, attack_success_column, mc_column, chernoff_column
from analysis.validation import monte_carlo_error_stats, chernoff_conservativeness_stats
from analysis.statistics import describe


ATTACK_CHOICES = ["bribery", "sybil", "ballot_stuffing", "all"]


def parse_args():
    p = argparse.ArgumentParser(description="E-voting attack simulation experiment runner.")
    p.add_argument("--trials", type=int, default=2500, help="Number of paired randomised trials.")
    p.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility.")
    p.add_argument("--attack", type=str, default="all", choices=ATTACK_CHOICES,
                   help="Which attack(s) to run.")
    p.add_argument("--mc-trials", type=int, default=MC_TRIALS_PER_SCENARIO,
                   help="Monte Carlo repetitions per scenario.")
    return p.parse_args()


def main():
    args = parse_args()
    attacks = ["bribery", "sybil", "ballot_stuffing"] if args.attack == "all" else [args.attack]

    os.makedirs(CSV_DIR, exist_ok=True)
    os.makedirs(JSON_DIR, exist_ok=True)

    print(f"[run_experiments] Running {args.trials} paired trials "
          f"(seed={args.seed}, attacks={attacks}, mc_trials={args.mc_trials})...")
    t0 = time.time()
    results = run_all_trials(n_trials=args.trials, seed=args.seed,
                              mc_trials=args.mc_trials, attacks=attacks)
    elapsed = time.time() - t0
    print(f"[run_experiments] Simulation complete in {elapsed:.2f}s.")

    # --- CSV export ---
    for key in ["bribery", "sybil", "ballot_stuffing"]:
        if key in results:
            path = os.path.join(CSV_DIR, f"{key}_results.csv")
            results[key].to_csv(path, index=False)
            print(f"[run_experiments] Wrote {path} ({len(results[key])} rows)")

    combined_path = os.path.join(CSV_DIR, "combined_results.csv")
    results["combined"].to_csv(combined_path, index=False)
    print(f"[run_experiments] Wrote {combined_path} ({len(results['combined'])} rows)")

    # --- Chernoff validation CSV (from bribery, which has full chernoff data) ---
    chernoff_rows = []
    for key in ["bribery", "sybil", "ballot_stuffing"]:
        if key not in results:
            continue
        df = results[key]
        exact_col = attack_success_column(key)
        mc_col = mc_column(key)
        ch_col = chernoff_column(key)
        sub = df[["trial_id", "system_type", exact_col, mc_col, ch_col]].copy()
        sub["attack_type"] = key
        sub = sub.rename(columns={exact_col: "exact_probability",
                                   mc_col: "monte_carlo_probability",
                                   ch_col: "chernoff_bound"})
        chernoff_rows.append(sub)
    if chernoff_rows:
        chernoff_df = pd.concat(chernoff_rows, ignore_index=True)
        chernoff_path = os.path.join(CSV_DIR, "chernoff_validation.csv")
        chernoff_df.to_csv(chernoff_path, index=False)
        print(f"[run_experiments] Wrote {chernoff_path} ({len(chernoff_df)} rows)")

    # --- Analysis ---
    summary = {
        "total_trials": args.trials,
        "seed": args.seed,
        "attacks_run": attacks,
        "mc_trials_per_scenario": args.mc_trials,
        "elapsed_seconds": elapsed,
    }

    countermeasure_effectiveness = {}
    monte_carlo_validation = {}
    chernoff_validation = {}
    certificate_validation = {}
    baseline_stats = {}
    protected_stats = {}
    threshold_m_stats = {}

    for key in ["bribery", "sybil", "ballot_stuffing"]:
        if key not in results:
            continue
        df = results[key]
        eff = compare_baseline_protected(df, key)
        countermeasure_effectiveness[key] = eff

        exact_col = attack_success_column(key)
        mc_col_name = mc_column(key)
        ch_col_name = chernoff_column(key)
        monte_carlo_validation[key] = monte_carlo_error_stats(df, exact_col=exact_col, mc_col=mc_col_name)
        chernoff_validation[key] = chernoff_conservativeness_stats(df, exact_col=exact_col, chernoff_col=ch_col_name)

        # Two-sided Chernoff certificate: unlike the one-sided bound above,
        # this yields a statement for EVERY scenario -- an upper bound on
        # success where the threshold sits above the mean, a lower bound
        # where it sits below. Recording how often the certified interval
        # actually contains the exact value is the validation that matters:
        # a single containment failure would mean a broken bound.
        lower = df["chernoff_success_lower"].fillna(0.0)
        upper = df["chernoff_success_upper"].fillna(1.0)
        contains = ((df[exact_col] >= lower - 1e-9) & (df[exact_col] <= upper + 1e-9))
        directions = df["chernoff_direction"].value_counts()
        certificate_validation[key] = {
            "n_rows": int(len(df)),
            "n_upper_bounded": int(directions.get("upper", 0)),
            "n_lower_bounded": int(directions.get("lower", 0)),
            "n_exact_by_construction": int(directions.get("impossible", 0)
                                           + directions.get("certain", 0)),
            "n_without_statement": int(df["chernoff_success_lower"].isna().sum()
                                       & df["chernoff_success_upper"].isna().sum()),
            "pct_interval_contains_exact": float(100.0 * contains.mean()),
            "mean_interval_width": float((upper - lower).mean()),
        }

        baseline_df = df[df.system_type == "baseline"]
        protected_df = df[df.system_type == "protected"]
        baseline_stats[key] = describe(baseline_df[exact_col])
        protected_stats[key] = describe(protected_df[exact_col])
        threshold_m_stats[key] = describe(df["m"])

    # --- Monte Carlo convergence sweep -------------------------------
    # The findings chapter states where the estimator settles. That claim
    # previously had no output backing it: convergence_curve() existed but
    # was never called. It is run here and written to CSV + summary, so
    # the sentence is data-derived like every other number in the report.
    from simulation.monte_carlo import convergence_curve
    conv_rng = np.random.default_rng(args.seed + 9901)
    conv_sizes = [10, 30, 100, 300, 1000, 3000, 10000, 30000, 50000]
    # A representative mid-range scenario: n and p taken from the same
    # illustrative setting Figure 7 uses, so the two agree.
    conv_n, conv_p, conv_m = 200, 0.55, 120
    conv = convergence_curve(conv_n, conv_p, conv_m, conv_sizes, conv_rng)
    conv_df = pd.DataFrame(conv)
    conv_df["two_se"] = 2.0 * np.sqrt(
        np.clip(conv_df["monte_carlo_estimate"] * (1 - conv_df["monte_carlo_estimate"]), 0, None)
        / conv_df["sample_size"])
    conv_df["within_two_se"] = conv_df["absolute_error"] <= conv_df["two_se"]
    conv_df.to_csv(os.path.join(CSV_DIR, "monte_carlo_convergence.csv"), index=False)
    # "Settles" = the smallest sample size from which the absolute error
    # stays below a fixed tolerance for THAT size and every larger one.
    # A 2-SE envelope alone is the wrong criterion here: it is a 95%
    # interval, so a single excursion is expected roughly one draw in
    # twenty and would make the reported figure jump around with the seed.
    # Both are recorded; the tolerance-based figure is the one quoted.
    CONV_TOL = 0.01
    errs = conv_df["absolute_error"].tolist()
    flags = conv_df["within_two_se"].tolist()
    def _settles(mask):
        for i, size in enumerate(conv_df["sample_size"]):
            if all(mask[i:]):
                return int(size)
        return None
    summary["monte_carlo_convergence"] = {
        "n": conv_n, "p": conv_p, "m": conv_m,
        "exact_probability": float(conv_df["exact_probability"].iloc[0]),
        "sample_sizes": conv_sizes,
        "tolerance": CONV_TOL,
        "settles_within_tolerance_from": _settles([e <= CONV_TOL for e in errs]),
        "settles_within_two_se_from": _settles(flags),
        "n_outside_two_se": int((~conv_df["within_two_se"]).sum()),
        "final_absolute_error": float(conv_df["absolute_error"].iloc[-1]),
    }

    summary["countermeasure_effectiveness"] = countermeasure_effectiveness
    summary["monte_carlo_validation"] = monte_carlo_validation
    summary["chernoff_validation"] = chernoff_validation
    summary["chernoff_certificate_validation"] = certificate_validation
    summary["baseline_statistics"] = baseline_stats
    summary["protected_statistics"] = protected_stats
    summary["threshold_m_statistics"] = threshold_m_stats

    # Most resilient attack (highest protected success probability)
    if protected_stats:
        most_resilient = max(protected_stats.items(), key=lambda kv: kv[1]["mean"])
        summary["most_resilient_attack_under_test_conditions"] = most_resilient[0]

    summary_path = os.path.join(JSON_DIR, "summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=float)
    print(f"[run_experiments] Wrote {summary_path}")

    print("[run_experiments] Done.")
    return results, summary


if __name__ == "__main__":
    main()
