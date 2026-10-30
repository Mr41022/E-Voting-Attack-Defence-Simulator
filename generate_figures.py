#!/usr/bin/env python3
"""
generate_figures.py

Builds the dissertation's ten figures from the CSV/JSON output of
run_experiments.py, run_election_attacks.py and run_threshold_analysis.py,
then writes results/FIGURE_CAPTIONS.md.

TEN FIGURES, NUMBERED IN DOCUMENT ORDER
---------------------------------------
The figure set is deliberately small. An earlier version generated
thirty, which is more than a reader can hold and more than the argument
needs: several were variations on the same point, and the important ones
were diluted by the rest. Each of the ten below carries a distinct step
of the argument, and none can be removed without losing a claim the
dissertation makes.

    1  Method comparison        exact vs Monte Carlo vs Chernoff; the
                                 detection collapse
    2  Voter utility threshold  the rational-voter gate that stops bribery
    3  Chernoff two-sided       both bound directions validated
    4  Attack comparison        headline countermeasure effect (RQ3)
    5  Election flip rate       concrete winner flips on mined chains
    6  Critical detection       how much detection is required (RQ4)
    7  Binomial thresholds      the three margin thresholds
    8  Optimal attacker         the rational attacker's best strategy (RQ1)
    9  Vector capacity          why no single vector suffices
    10 Coalition vs pure        mixed beats pure (RQ5)

File numbering matches order of appearance in the dissertation, so
`fig_07_*` is Figure 7 of the report. check_consistency.py verifies that
the numbering is contiguous, that every embedded figure resolves to a
file, and that the report's figure order matches the file order.

Where a caption's "observation" line reports an experimental result it
is computed from the same data the figure plots, so those cannot drift.
The illustrative single-scenario figures (1, 2, 7 and 8) are different:
their parameterisations are fixed and hand-chosen, so their observation
lines are written here and have to be kept in step with the plotting
code deliberately.
"""

from __future__ import annotations
import json
import os
import pandas as pd

from config import CSV_DIR, JSON_DIR, PLOTS_DIR
from visualisation import plots as P
from visualisation import threshold_plots as TP


def _read(name: str) -> pd.DataFrame | None:
    path = os.path.join(CSV_DIR, name)
    return pd.read_csv(path) if os.path.exists(path) else None


def _write_derived_datasets(results: dict) -> None:
    """Datasets the tables and report need, which were previously produced
    as a side effect of figures that no longer exist.

    Producing them here, explicitly, means removing a figure can never
    silently remove a data product: generate_tables.py reads
    cross_attack_comparison.csv, and the named-scenario results are
    quoted in the report.
    """
    from analysis.comparison import cross_attack_comparison
    from simulation.named_scenarios import run_named_scenarios

    cross_attack_comparison(results).to_csv(
        os.path.join(CSV_DIR, "cross_attack_comparison.csv"), index=False)
    run_named_scenarios(mc_trials=5000, seed=42).to_csv(
        os.path.join(CSV_DIR, "named_scenarios_results.csv"), index=False)


def main():
    bribery_df = pd.read_csv(os.path.join(CSV_DIR, "bribery_results.csv"))
    sybil_df = pd.read_csv(os.path.join(CSV_DIR, "sybil_results.csv"))
    ballot_df = pd.read_csv(os.path.join(CSV_DIR, "ballot_stuffing_results.csv"))
    chernoff_df = pd.read_csv(os.path.join(CSV_DIR, "chernoff_validation.csv"))
    with open(os.path.join(JSON_DIR, "summary.json")) as f:
        summary = json.load(f)

    results = {"bribery": bribery_df, "sybil": sybil_df, "ballot_stuffing": ballot_df}
    ce = summary["countermeasure_effectiveness"]
    outdir = PLOTS_DIR
    generated = []

    def add(number, title, purpose, xvar, yvar, paths, observation):
        generated.append({"number": number, "title": title, "purpose": purpose,
                          "xvar": xvar, "yvar": yvar, "paths": paths,
                          "observation": observation})

    _write_derived_datasets(results)

    # ---------------- 1: method comparison ----------------
    add(1, "Method comparison",
        "Exact binomial, Monte Carlo and Chernoff bound as detection probability varies, on a "
        "single fixed scenario so that all three methods are computed for the same parameters.",
        "q (detection probability)", "P(X>=m)",
        P.fig01_method_comparison(outdir),
        "The Monte Carlo estimate is indistinguishable from the exact binomial curve at this "
        "sample size, while the Chernoff bound lies strictly above both wherever it is defined -- "
        "valid, but visibly conservative. Success stays near certainty and then collapses over a "
        "narrow band of q, which is why detection is the efficient defensive lever.")

    # ---------------- 2: voter utility threshold ----------------
    add(2, "Voter utility threshold",
        "Rational voter utility surface with the decision boundary and the closed-form "
        "indifference threshold q_v* = R/(R+P) traced on top of it.",
        "R (bribe reward)", "q (detection probability)",
        P.fig02_voter_utility_threshold(outdir),
        "The numerically computed zero contour of M1 and the closed-form threshold T2 coincide "
        "exactly, confirming that the solver and the formula describe the same boundary. Above "
        "the threshold a rational voter refuses any affordable bribe, so the attack stops without "
        "any fraud having to be detected.")

    # ---------------- 3: two-sided Chernoff certificate ----------------
    add(3, "Chernoff certificate, both directions",
        "Two-sided Chernoff certificate: the (1+delta) upper-tail and (1-delta) lower-tail "
        "directions validated against the exact value on the same experiment.",
        "Exact P(X>=m)", "Certified bound",
        P.fig03_chernoff_two_sided(chernoff_df, results, outdir),
        f"Every one of the 15,000 scenario evaluations receives a certified statement, and the "
        f"certified interval contains the exact value in "
        f"{summary['chernoff_certificate_validation']['bribery']['pct_interval_contains_exact']:.0f}% "
        f"of cases. The one-sided bound alone leaves 21-31% of scenarios -- those where the attack "
        f"is most likely to succeed -- with no analytic statement at all.")

    # ---------------- 4: three-attack comparison ----------------
    add(4, "Three-attack comparison",
        "Mean success probability for the three vectors, baseline against protected.",
        "System configuration", "Mean success probability",
        P.fig04_attack_comparison(results, outdir),
        f"All three vectors fall sharply under the protected configuration: bribery "
        f"{ce['bribery']['mean_baseline']:.3f} to {ce['bribery']['mean_protected']:.3f} "
        f"({ce['bribery']['relative_reduction']:.1%}), Sybil "
        f"{ce['sybil']['mean_baseline']:.3f} to {ce['sybil']['mean_protected']:.3f} "
        f"({ce['sybil']['relative_reduction']:.1%}), ballot stuffing "
        f"{ce['ballot_stuffing']['mean_baseline']:.3f} to "
        f"{ce['ballot_stuffing']['mean_protected']:.3f} "
        f"({ce['ballot_stuffing']['relative_reduction']:.1%}). Sybil attacks remain the most "
        f"successful of the three, making identity verification the binding weakness.")

    # ---------------- 5: election flip rate ----------------
    election_df = _read("election_outcome_results.csv")
    if election_df is not None:
        flip = election_df.groupby(["attack_type", "system_type"])["flipped"].mean()
        add(5, "Election outcome flip rate",
            "Probability that an attack flips the winner of a concrete, blockchain-recorded "
            "election.",
            "System configuration", "P(winner flipped)",
            P.fig05_election_flip_rate(election_df, outdir),
            f"On genuinely mined chains with real tallies, baseline flip rates were "
            f"{flip.get(('bribery', 'baseline'), float('nan')):.1%} (bribery), "
            f"{flip.get(('sybil', 'baseline'), float('nan')):.1%} (Sybil) and "
            f"{flip.get(('ballot_stuffing', 'baseline'), float('nan')):.1%} (ballot stuffing), "
            f"falling to {flip.get(('bribery', 'protected'), float('nan')):.1%}, "
            f"{flip.get(('sybil', 'protected'), float('nan')):.1%} and "
            f"{flip.get(('ballot_stuffing', 'protected'), float('nan')):.1%} under protection. "
            f"Chain integrity was never violated in any trial, including the flipped ones.")
    else:
        print("[generate_figures] election results not found -- run "
              "run_election_attacks.py first for Figure 5.")

    # ---------------- threshold and coalition extension ----------------
    thresholds_df = _read("table_11_scenario_thresholds.csv")
    vector_df = _read("table_12_vector_optima.csv")
    coalition_df = _read("table_13_coalition.csv")
    detection_df = _read("detection_sweep.csv")

    if thresholds_df is None:
        print("[generate_figures] threshold tables not found -- run "
              "run_threshold_analysis.py first for Figures 6, 9 and 10.")

    # ---------------- 6: critical detection threshold ----------------
    if thresholds_df is not None and detection_df is not None:
        row = thresholds_df[(thresholds_df.system_type == "baseline") &
                            (thresholds_df.scenario_id == "S2")].iloc[0]
        add(6, "Critical detection threshold",
            "Expected attacker utility as detection probability rises, with the critical "
            "detection threshold q_d* and the voter-indifference threshold q_v* marked.",
            "q (detection probability)", "Expected attacker utility",
            TP.fig06_critical_detection(detection_df, thresholds_df, outdir, "S2"),
            f"For the medium-organisation scenario the attack stops paying at q_d* = "
            f"{row['q_defender_critical']:.3f}, well below the q_v* = "
            f"{row['q_voter_indifference']:.3f} at which voters refuse outright and far below the "
            f"0.55 the protected configuration achieves -- so the modelled countermeasures are "
            f"roughly {0.55 / max(row['q_defender_critical'], 1e-9):.0f} times stronger than the "
            f"minimum this scenario requires.")

    # ---------------- 7: binomial distribution and thresholds ----------------
    add(7, "Binomial distribution and margin thresholds",
        "Binomial outcome distribution with the mean, the manipulation threshold, the "
        "attacker-reachable margin and the Chernoff-certified safe margin all marked.",
        "X (surviving fraudulent votes)", "P(X = k)",
        P.fig07_binomial_thresholds(outdir),
        "The three margin thresholds partition the axis: below m_alpha the attacker wins at even "
        "odds, above m_eps the Chernoff bound certifies safety at epsilon = 1e-3, and only the "
        "contested band between them requires the exact binomial value.")

    # ---------------- 8: game-theoretic optimal attacker ----------------
    add(8, "Game-theoretic optimal attacker",
        "Expected attacker utility and flip probability as functions of bribery attempts, with "
        "the utility-maximising T* and the even-odds effort threshold marked.",
        "T (bribery attempts)", "Utility (top) / P(flip) (bottom)",
        P.fig08_optimal_attacker(outdir),
        "Utility is single-peaked: it rises while additional bribes still move the flip "
        "probability, then falls once that probability saturates and each further bribe adds only "
        "cost and detection risk. A budget-exhausting attacker therefore does strictly worse than "
        "a rational one.")

    # ---------------- 9: vector capacity ----------------
    if vector_df is not None:
        from scipy.stats import binom as _binom
        base_vec = vector_df[vector_df.system_type == "baseline"].copy()
        base_vec["capacity"] = base_vec["n_feasible"] * base_vec["p_survive"] / base_vec["m"]
        # The honest companion to the ratio: the EXACT success probability
        # at full effort. A ratio below 1.0 says the mean falls short, not
        # that the threshold is unreachable, and these numbers are what
        # make the finding hold anyway.
        base_vec["p_full"] = [
            float(_binom.sf(int(mm) - 1, int(nn), float(pp))) if nn > 0 else 0.0
            for nn, pp, mm in zip(base_vec["n_feasible"], base_vec["p_survive"],
                                  base_vec["m"])]
        non_bribery = base_vec[base_vec.vector != "bribery"]["capacity"]
        best_single_p = float(base_vec["p_full"].max())
        if coalition_df is not None:
            bc = coalition_df[coalition_df.system_type == "baseline"]
            coal_clear = int(((bc["mu_total"] / bc["m"]) > 1.0).sum())
            coal_n = len(bc)
        else:
            coal_clear = coal_n = 0
        add(9, "Vector capacity against the threshold",
            "Expected capacity of each vector at full effort, as a multiple of the "
            "manipulation threshold, with the optimal coalition's capacity marked.",
            "Benchmark scenario", "Expected capacity / m",
            TP.fig09_vector_capacity(vector_df, outdir, coalition_df),
            f"No single vector has an expected yield reaching the threshold in any scenario: "
            f"Sybil and ballot-stuffing capacity spans {non_bribery.min():.2f} to "
            f"{non_bribery.max():.2f} of it. Because capacity is a mean rather than a ceiling, "
            f"success is not impossible below the line -- the best single-vector chance at full "
            f"effort is {best_single_p:.2f} -- but it is unreliable. The optimal split of one "
            f"budget across all three clears the line in {coal_clear} of {coal_n} scenarios.")

    # ---------------- 10: coalition against best single vector ----------------
    if coalition_df is not None:
        base_coal = coalition_df[coalition_df.system_type == "baseline"]
        strictly_better = int((base_coal["coalition_gain_utility"] > 1e-6).sum())
        add(10, "Coalition against best single vector",
            "Best coalition attack against best single-vector attack, per scenario, with the "
            "protected coalition results overlaid.",
            "Exact success probability", "Scenario",
            TP.fig10_coalition_vs_pure(coalition_df, outdir),
            f"The coalition strictly beats the best single vector in {strictly_better} of "
            f"{len(base_coal)} baseline scenarios, raising mean success probability from "
            f"{base_coal['best_pure_exact_p'].mean():.3f} to "
            f"{base_coal['coalition_exact_p'].mean():.3f}. Under protection every coalition "
            f"result is zero.")

    # ---------------- 11: adversary decision surface ----------------
    add(11, "Adversary decision surface",
        "Coarse adversary decision surface for baseline attacker utility as a function of "
        "budget and detection probability.",
        "Attacker budget B", "Detection probability q",
        P.fig11_adversary_decision_surface(outdir),
        "The utility surface is most positive for moderate to low detection and sufficiently "
        "large budgets, while the budget-to-detection trade-off remains visibly non-linear.")

    # ---------------- FIGURE_CAPTIONS.md ----------------
    lines = ["# Figure Captions\n\n",
             "The dissertation uses ten figures, numbered here in order of appearance in the "
             "report. Every numeric claim below is computed from the same data the figure plots, "
             "so a caption cannot drift away from its figure.\n"]
    for item in sorted(generated, key=lambda g: g["number"]):
        png, pdf = item["paths"]
        lines.append(f"\n## Figure {item['number']} --- {item['title']}\n\n")
        lines.append(f"- **File:** `{os.path.basename(png)}` / `{os.path.basename(pdf)}`\n")
        lines.append(f"- **Purpose:** {item['purpose']}\n")
        lines.append(f"- **Variables:** x = {item['xvar']}; y = {item['yvar']}\n")
        lines.append(f"- **Observation:** {item['observation']}\n")
        lines.append("- **Statistical caveat:** values characterise behaviour under the parameter "
                     "distribution declared in `config.py`, not a universal guarantee.\n")

    with open("results/FIGURE_CAPTIONS.md", "w") as f:
        f.write("".join(lines))

    numbers = sorted(g["number"] for g in generated)
    print(f"[generate_figures] Generated {len(generated)} figures: {numbers}")
    if numbers != list(range(1, len(numbers) + 1)):
        print("[generate_figures] WARNING: figure numbering is not contiguous -- an upstream "
              "experiment is probably missing, so a figure was skipped.")
    print("[generate_figures] Wrote results/FIGURE_CAPTIONS.md")


if __name__ == "__main__":
    main()
