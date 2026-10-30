"""Cross-table reporting consistency.

Sybil and ballot stuffing pass fraudulent votes through two independent
gates -- acceptance and detection -- so they have two different success
probabilities:

    accepted_ge_m    clears the ACCEPTANCE gate only (intermediate)
    surviving_ge_m   clears BOTH gates (the headline measure)

An earlier version of Tables 3-5 reported the first under the bare
heading "mean" while Tables 7-9 and Figure 4 reported the second. Both
numbers were correct; nothing in the output said they were different
statistics, so a reader comparing tables saw an unexplained mismatch
(0.5366 against 0.4804 for Sybil, 0.4979 against 0.4416 for ballot
stuffing). That was raised in review.

These tests pin the reconciliation: the measures must stay labelled,
must stay ordered (acceptance-only can never be smaller than
both-gates), and the table a reader is most likely to quote must carry
the same numbers as the headline analysis.
"""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CSV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "results", "csv")

TOL = 5e-4      # tables are published to 4 decimal places


def _load(name):
    return pd.read_csv(os.path.join(CSV, name + ".csv"))


def _mean(df, attack, measure, system):
    row = df[(df.attack == attack) & (df.measure == measure) &
             (df.system == system)]
    assert len(row) == 1, f"expected one row for {attack}/{measure}/{system}"
    return float(row["mean"].iloc[0])


def test_per_attack_tables_name_the_measure_they_report():
    """No table may report a success probability under a bare 'mean'."""
    for name in ["table_02_bribery_results", "table_03_sybil_results",
                 "table_04_ballot_stuffing_results",
                 "table_05_baseline_vs_protected"]:
        df = _load(name)
        assert "measure" in df.columns, f"{name} does not name its measure"
        assert "measure_definition" in df.columns, f"{name} does not define its measure"
        assert df["measure_definition"].notna().all()


def test_two_gate_attacks_report_both_measures():
    """Sybil and ballot stuffing must publish acceptance-only AND both-gates."""
    for name, attack in [("table_03_sybil_results", "sybil"),
                         ("table_04_ballot_stuffing_results", "ballot_stuffing")]:
        df = _load(name)
        measures = set(df["measure"])
        assert measures == {"surviving_ge_m", "accepted_ge_m"}, (
            f"{attack} reports {measures}; both gates and acceptance-only are required")
        assert set(df["system"]) == {"baseline", "protected"}


def test_acceptance_only_is_never_below_both_gates():
    """Ordering follows from the model: a second gate can only remove votes.

    If this ever inverted, one of the two columns would be mislabelled.
    """
    for name, attack in [("table_03_sybil_results", "sybil"),
                         ("table_04_ballot_stuffing_results", "ballot_stuffing")]:
        df = _load(name)
        for system in ["baseline", "protected"]:
            accepted = _mean(df, attack, "accepted_ge_m", system)
            surviving = _mean(df, attack, "surviving_ge_m", system)
            assert accepted >= surviving - 1e-12, (
                f"{attack}/{system}: acceptance-only ({accepted:.4f}) is below "
                f"both-gates ({surviving:.4f}) -- the labels are swapped")


def test_headline_tables_agree_across_the_report():
    """Table 5 must carry the same numbers as Tables 7, 8 and 9.

    This is the check that would have caught the reported mismatch.
    """
    t5 = _load("table_05_baseline_vs_protected")
    t7 = _load("table_07_statistical_analysis")
    t8 = _load("table_08_countermeasure_effectiveness")
    t9 = _load("table_09_overall_comparison")

    for attack in ["bribery", "sybil", "ballot_stuffing"]:
        measure = "single_gate" if attack == "bribery" else "surviving_ge_m"
        base_5 = _mean(t5, attack, measure, "baseline")
        prot_5 = _mean(t5, attack, measure, "protected")

        for name, df, bcol, pcol, key in [
                ("Table 7", t7, "mean_baseline", "mean_protected", "attack_type"),
                ("Table 8", t8, "mean_baseline", "mean_protected", "attack_type"),
                ("Table 9", t9, "mean_baseline_success", "mean_protected_success",
                 "attack")]:
            row = df[df[key] == attack]
            assert len(row) == 1, f"{name} has no row for {attack}"
            assert abs(float(row[bcol].iloc[0]) - base_5) < TOL, (
                f"{name} baseline for {attack} disagrees with Table 5: "
                f"{float(row[bcol].iloc[0]):.4f} vs {base_5:.4f}")
            assert abs(float(row[pcol].iloc[0]) - prot_5) < TOL, (
                f"{name} protected for {attack} disagrees with Table 5: "
                f"{float(row[pcol].iloc[0]):.4f} vs {prot_5:.4f}")


def test_bribery_reports_a_single_gate():
    """Bribery folds detection into 1-q, so it has one measure, not two."""
    t2 = _load("table_02_bribery_results")
    assert set(t2["measure"]) == {"single_gate"}
    assert len(t2) == 2      # baseline and protected, one measure each
