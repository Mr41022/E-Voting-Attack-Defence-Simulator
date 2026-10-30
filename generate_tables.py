#!/usr/bin/env python3
"""
generate_tables.py

Generates thesis tables (CSV + LaTeX) from the experimental results.
"""
from __future__ import annotations
import json
import os
import pandas as pd

from config import CSV_DIR, JSON_DIR, LATEX_DIR, PARAM_RANGES


def df_to_latex(df: pd.DataFrame, caption: str, label: str) -> str:
    return df.to_latex(index=False, float_format="%.4f", caption=caption, label=label,
                        escape=True)


def main():
    os.makedirs(LATEX_DIR, exist_ok=True)
    with open(os.path.join(JSON_DIR, "summary.json")) as f:
        summary = json.load(f)

    bribery_df = pd.read_csv(os.path.join(CSV_DIR, "bribery_results.csv"))
    sybil_df = pd.read_csv(os.path.join(CSV_DIR, "sybil_results.csv"))
    ballot_df = pd.read_csv(os.path.join(CSV_DIR, "ballot_stuffing_results.csv"))
    cross_df = pd.read_csv(os.path.join(CSV_DIR, "cross_attack_comparison.csv"))
    chernoff_df = pd.read_csv(os.path.join(CSV_DIR, "chernoff_validation.csv"))

    # TABLE 1: parameter ranges
    t1_rows = [{"parameter": k, "low": v[0], "high": v[1]} for k, v in PARAM_RANGES.items()]
    t1 = pd.DataFrame(t1_rows)
    t1.to_csv(f"{CSV_DIR}/table_01_parameter_ranges.csv", index=False)

    # TABLE 2/3/4: attack results summary stats
    #
    # TWO DISTINCT MEASURES, REPORTED SIDE BY SIDE AND NAMED
    # -----------------------------------------------------
    # Sybil and ballot stuffing pass fraudulent votes through TWO
    # independent gates: acceptance (registration / ballot admission)
    # and detection. That yields two different probabilities, and an
    # earlier version of these tables reported only the first under the
    # bare heading "mean", which invited the reader to compare it with
    # the headline figure in Tables 7-9 -- a different statistic.
    #
    #   accepted_ge_m   P(at least m fraudulent votes clear the
    #                   ACCEPTANCE gate). An intermediate quantity: it
    #                   ignores detection, so it is always the larger of
    #                   the two and is NOT comparable across attacks.
    #
    #   surviving_ge_m  P(at least m fraudulent votes clear BOTH gates,
    #                   i.e. are accepted AND escape detection). This is
    #                   the headline attack-success measure and the one
    #                   used in Tables 7-9, Figure 4 and every stated
    #                   conclusion.
    #
    # Bribery has a single effective gate -- detection is already folded
    # into its per-attempt success probability 1-q -- so the two measures
    # coincide there and it reports one row per system.
    MEASURE_LABELS = {
        "accepted_ge_m": "P(accepted >= m): acceptance gate only",
        "surviving_ge_m": "P(surviving >= m): both gates -- HEADLINE",
        "single_gate": "P(success >= m): single gate -- HEADLINE",
    }

    def summarise(df, attack_name, measures):
        """measures: list of (column, measure_key) in reporting order."""
        rows = []
        for col, key in measures:
            for label in ["baseline", "protected"]:
                sub = df[df.system_type == label][col]
                rows.append({
                    "attack": attack_name,
                    "measure": key,
                    "measure_definition": MEASURE_LABELS[key],
                    "system": label,
                    "mean": sub.mean(), "median": sub.median(), "std": sub.std(),
                    "min": sub.min(), "max": sub.max(),
                })
        return pd.DataFrame(rows)

    t2 = summarise(bribery_df, "bribery",
                   [("exact_probability", "single_gate")])
    t2.to_csv(f"{CSV_DIR}/table_02_bribery_results.csv", index=False)
    t3 = summarise(sybil_df, "sybil",
                   [("surviving_ge_m_exact_probability", "surviving_ge_m"),
                    ("exact_probability_accepted_ge_m", "accepted_ge_m")])
    t3.to_csv(f"{CSV_DIR}/table_03_sybil_results.csv", index=False)
    t4 = summarise(ballot_df, "ballot_stuffing",
                   [("surviving_ge_m_exact_probability", "surviving_ge_m"),
                    ("exact_probability_accepted_ge_m", "accepted_ge_m")])
    t4.to_csv(f"{CSV_DIR}/table_04_ballot_stuffing_results.csv", index=False)

    # TABLE 5: baseline vs protected combined -- headline measure only, so
    # that the one table a reader is most likely to quote carries exactly
    # the numbers that appear in Tables 7-9 and Figure 4.
    t5 = pd.concat([t2, t3, t4], ignore_index=True)
    t5 = t5[t5.measure != "accepted_ge_m"].reset_index(drop=True)
    t5.to_csv(f"{CSV_DIR}/table_05_baseline_vs_protected.csv", index=False)

    # TABLE 6: chernoff validation
    t6_rows = []
    for atk in ["bribery", "sybil", "ballot_stuffing"]:
        v = summary["chernoff_validation"][atk]
        v["attack"] = atk
        t6_rows.append(v)
    t6 = pd.DataFrame(t6_rows)
    t6.to_csv(f"{CSV_DIR}/table_06_chernoff_validation.csv", index=False)

    # TABLE 7: statistical / effect sizes (cross_df already has bootstrap CIs)
    t7 = cross_df.copy()
    t7.to_csv(f"{CSV_DIR}/table_07_statistical_analysis.csv", index=False)

    # TABLE 8: countermeasure effectiveness (subset of t7)
    t8 = cross_df[["attack_type", "mean_baseline", "mean_protected",
                    "absolute_reduction", "relative_reduction"]].copy()
    t8.to_csv(f"{CSV_DIR}/table_08_countermeasure_effectiveness.csv", index=False)

    # TABLE 9: overall attack comparison
    t9_rows = []
    for atk in ["bribery", "sybil", "ballot_stuffing"]:
        mc = summary["monte_carlo_validation"][atk]
        ch = summary["chernoff_validation"][atk]
        ce = summary["countermeasure_effectiveness"][atk]
        t9_rows.append({
            "attack": atk,
            "mean_baseline_success": ce["mean_baseline"],
            "mean_protected_success": ce["mean_protected"],
            "relative_reduction_pct": ce["relative_reduction"] * 100,
            "mc_mean_abs_error": mc.get("mean_absolute_error"),
            "chernoff_pct_holds": ch.get("pct_bound_holds"),
        })
    t9 = pd.DataFrame(t9_rows)
    t9.to_csv(f"{CSV_DIR}/table_09_overall_comparison.csv", index=False)

    # TABLE 10: sample of individual randomised scenarios showing the
    # manipulation threshold m explicitly alongside N and outcome, for
    # direct citation in the thesis text (illustrates concrete trials
    # rather than only aggregate means).
    sample_cols_bribery = ["trial_id", "N", "m", "B", "R", "P", "q", "system_type",
                            "exact_probability", "attack_success_exact"]
    t10 = bribery_df[sample_cols_bribery].sort_values("trial_id").head(30)
    t10.to_csv(f"{CSV_DIR}/table_10_sample_scenarios_with_threshold.csv", index=False)

    # --- LaTeX exports (subset, per spec section 30) ---
    with open(f"{LATEX_DIR}/table_attack_comparison.tex", "w") as f:
        f.write(df_to_latex(t9, "Overall attack comparison across bribery, Sybil, and ballot stuffing attacks.",
                             "tab:attack_comparison"))
    with open(f"{LATEX_DIR}/table_chernoff_validation.tex", "w") as f:
        f.write(df_to_latex(t6, "Chernoff bound validation statistics.", "tab:chernoff_validation"))
    with open(f"{LATEX_DIR}/table_countermeasure_effectiveness.tex", "w") as f:
        f.write(df_to_latex(t8, "Countermeasure effectiveness (absolute and relative reduction).",
                             "tab:countermeasure_effectiveness"))

    print("[generate_tables] Wrote tables 1-9 as CSV to results/csv/")
    print("[generate_tables] Wrote 3 LaTeX tables to results/latex/")


if __name__ == "__main__":
    main()
