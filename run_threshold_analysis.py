"""
run_threshold_analysis.py

CLI entry point for the threshold and coalition extension (T1-T7, G1-G2).

Writes, into results/:
    csv/table_11_scenario_thresholds.csv     every threshold, every scenario
    csv/table_12_vector_optima.csv           optimal effort per vector (G1)
    csv/table_13_coalition.csv               optimal budget split (G2)
    csv/detection_sweep.csv                  utility vs q, per scenario
    csv/budget_sweep.csv                     utility vs B, per scenario
    csv/table_14_cost_sensitivity.csv        robustness of the G2 conclusion
    json/threshold_analysis.json             machine-readable summary

Deterministic: every quantity here is analytic (exact binomial, exact
convolution, bisection on a monotone function), so no seed is required
and repeated runs are bit-for-bit identical.

Usage:
    python run_threshold_analysis.py
    python run_threshold_analysis.py --grid-step 0.05
"""

from __future__ import annotations

import argparse
import json
import os
import time
from typing import Dict, List

import pandas as pd

import config
from attacks.game_theory import coalition_attack, optimal_coalition
from simulation import threshold_analysis as ta
from simulation.named_scenarios import SCENARIOS


def _cost_sensitivity(grid_step: float) -> pd.DataFrame:
    """Does the coalition conclusion survive different relative costs and
    capacity ceilings? Re-runs the S1/S2 optimisation across a grid of
    the four modelling constants declared in threshold_analysis.py and
    records whether the coalition still beats the best pure vector.
    """
    rows: List[Dict] = []
    original = (ta.IDENTITY_COST_RATIO, ta.BALLOT_COST_RATIO,
                ta.SYBIL_CEILING_FRACTION, ta.BALLOT_CEILING_FRACTION)
    try:
        for id_ratio in (0.2, 0.4, 0.8):
            for ballot_ratio in (0.05, 0.15, 0.40):
                for sybil_ceiling in (0.10, 0.20):
                    for ballot_ceiling in (0.15, 0.30):
                        ta.IDENTITY_COST_RATIO = id_ratio
                        ta.BALLOT_COST_RATIO = ballot_ratio
                        ta.SYBIL_CEILING_FRACTION = sybil_ceiling
                        ta.BALLOT_CEILING_FRACTION = ballot_ceiling
                        for scenario in SCENARIOS[:3]:
                            specs, gates = ta.build_specs(scenario, "baseline")
                            best, _ = optimal_coalition(specs, scenario.m, scenario.B,
                                                        scenario.V, scenario.D_attack,
                                                        gates, grid_step=grid_step)
                            pure_best = max(
                                (coalition_attack(specs, scenario.m, scenario.B,
                                                  [1.0 if j == i else 0.0
                                                   for j in range(3)],
                                                  scenario.V, scenario.D_attack, gates)
                                 for i in range(3)),
                                key=lambda r: r.utility)
                            rows.append({
                                "scenario_id": scenario.scenario_id,
                                "identity_cost_ratio": id_ratio,
                                "ballot_cost_ratio": ballot_ratio,
                                "sybil_ceiling_fraction": sybil_ceiling,
                                "ballot_ceiling_fraction": ballot_ceiling,
                                "coalition_exact_p": best.exact_p_success,
                                "best_pure_exact_p": pure_best.exact_p_success,
                                "coalition_utility": best.utility,
                                "best_pure_utility": pure_best.utility,
                                "coalition_at_least_as_good":
                                    best.utility >= pure_best.utility - 1e-6,
                                "coalition_strictly_better":
                                    best.utility > pure_best.utility + 1e-6,
                            })
    finally:
        (ta.IDENTITY_COST_RATIO, ta.BALLOT_COST_RATIO,
         ta.SYBIL_CEILING_FRACTION, ta.BALLOT_CEILING_FRACTION) = original
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Threshold and coalition analysis")
    parser.add_argument("--grid-step", type=float, default=0.05,
                        help="budget-simplex resolution for the coalition search")
    parser.add_argument("--skip-sensitivity", action="store_true",
                        help="skip the cost/ceiling robustness sweep")
    args = parser.parse_args()

    os.makedirs(config.CSV_DIR, exist_ok=True)
    os.makedirs(config.JSON_DIR, exist_ok=True)
    start = time.time()

    print("[thresholds] Solving critical thresholds T1-T7 for 5 named scenarios...")
    thresholds = ta.compute_scenario_thresholds()
    thresholds.to_csv(f"{config.CSV_DIR}/table_11_scenario_thresholds.csv", index=False)

    print("[thresholds] Optimising single-vector effort (G1)...")
    vector_optima = ta.compute_single_vector_optima()
    vector_optima.to_csv(f"{config.CSV_DIR}/table_12_vector_optima.csv", index=False)

    print(f"[thresholds] Searching coalition budget simplex (G2, step={args.grid_step})...")
    coalition = ta.compute_coalition_results(grid_step=args.grid_step)
    coalition.to_csv(f"{config.CSV_DIR}/table_13_coalition.csv", index=False)

    print("[thresholds] Sweeping detection probability and budget...")
    detection = pd.concat([ta.detection_sweep(s) for s in SCENARIOS], ignore_index=True)
    detection.to_csv(f"{config.CSV_DIR}/detection_sweep.csv", index=False)
    budget = pd.concat([ta.budget_sweep(s) for s in SCENARIOS], ignore_index=True)
    budget.to_csv(f"{config.CSV_DIR}/budget_sweep.csv", index=False)

    sensitivity = pd.DataFrame()
    if not args.skip_sensitivity:
        print("[thresholds] Running cost/ceiling robustness sweep...")
        sensitivity = _cost_sensitivity(grid_step=max(args.grid_step, 0.1))
        sensitivity.to_csv(f"{config.CSV_DIR}/table_14_cost_sensitivity.csv", index=False)

    baseline = coalition[coalition.system_type == "baseline"]
    protected = coalition[coalition.system_type == "protected"]
    thr_base = thresholds[thresholds.system_type == "baseline"]
    thr_prot = thresholds[thresholds.system_type == "protected"]

    summary = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_seconds": round(time.time() - start, 2),
        "grid_step": args.grid_step,
        "cost_model": {
            "identity_cost_ratio": ta.IDENTITY_COST_RATIO,
            "ballot_cost_ratio": ta.BALLOT_COST_RATIO,
            "sybil_ceiling_fraction": ta.SYBIL_CEILING_FRACTION,
            "ballot_ceiling_fraction": ta.BALLOT_CEILING_FRACTION,
            "certification_epsilon": ta.CERTIFICATION_EPSILON,
            "reachable_alpha": ta.REACHABLE_ALPHA,
        },
        "voter_gate": {
            "q_voter_indifference_by_scenario": {
                r.scenario_id: r.q_voter_indifference for r in thr_base.itertuples()
            },
            "protected_q": float(thr_prot["q"].iloc[0]),
            "n_scenarios_gate_open_baseline": int(thr_base["voter_accepts"].sum()),
            "n_scenarios_gate_open_protected": int(thr_prot["voter_accepts"].sum()),
        },
        "critical_detection": {
            r.scenario_id: r.q_defender_critical for r in thr_base.itertuples()
        },
        "break_even_budget": {
            r.scenario_id: r.B_star for r in thr_base.itertuples()
        },
        "coalition": {
            "mean_baseline_exact_p": float(baseline["coalition_exact_p"].mean()),
            "mean_protected_exact_p": float(protected["coalition_exact_p"].mean()),
            "mean_gain_over_best_pure_baseline": float(baseline["coalition_gain_p"].mean()),
            "n_scenarios_coalition_strictly_better":
                int((baseline["coalition_gain_utility"] > 1e-6).sum()),
            "per_scenario": {
                r.scenario_id: {
                    "shares": {"bribery": r.share_bribery, "sybil": r.share_sybil,
                               "ballot_stuffing": r.share_ballot_stuffing},
                    "coalition_exact_p": r.coalition_exact_p,
                    "best_pure_vector": r.best_pure_vector,
                    "best_pure_exact_p": r.best_pure_exact_p,
                } for r in baseline.itertuples()
            },
        },
    }
    if not sensitivity.empty:
        summary["sensitivity"] = {
            "n_configurations": int(len(sensitivity)),
            "pct_coalition_at_least_as_good":
                float(100.0 * sensitivity["coalition_at_least_as_good"].mean()),
            "pct_coalition_strictly_better":
                float(100.0 * sensitivity["coalition_strictly_better"].mean()),
        }

    with open(f"{config.JSON_DIR}/threshold_analysis.json", "w") as fh:
        json.dump(summary, fh, indent=2)

    print(f"[thresholds] Done in {summary['elapsed_seconds']}s.")
    print(f"[thresholds] Wrote 6 CSV tables to {config.CSV_DIR}/")
    print(f"[thresholds] Wrote {config.JSON_DIR}/threshold_analysis.json")
    gate_open_protected = summary["voter_gate"]["n_scenarios_gate_open_protected"]
    print(f"  bribery incentive-compatible under protection in "
          f"{gate_open_protected}/{len(SCENARIOS)} scenarios")
    print(f"  coalition strictly beats best single vector in "
          f"{summary['coalition']['n_scenarios_coalition_strictly_better']}"
          f"/{len(SCENARIOS)} baseline scenarios")


if __name__ == "__main__":
    main()
