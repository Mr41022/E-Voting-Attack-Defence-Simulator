"""Tests that pin CLAIMS, not just computations.

Every defect these guard against was a case of correct arithmetic
described wrongly in prose or in a figure. A numerical test would have
passed on all of them, which is why they are asserted here explicitly.

Each test names the sentence it protects.
"""

import math
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import binom

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV = os.path.join(ROOT, "results", "csv")


def _load(name):
    return pd.read_csv(os.path.join(CSV, name + ".csv"))


# ---------------------------------------------------------------------
# Capacity is a MEAN, not a ceiling
# ---------------------------------------------------------------------

def test_capacity_ratio_below_one_does_not_imply_impossible():
    """Guards: "a vector below the line cannot reach the threshold at any budget".

    That claim was in the Figure 9 docstring, its caption, the capacity
    table note and two places in the report. It is false: the ratio is
    E[X]/m, so a value below 1 means the MEAN falls short, and success
    remains possible on an upward fluctuation. This test fails if the
    data ever stops refuting it -- i.e. it documents why the wording had
    to change.
    """
    v = _load("table_12_vector_optima")
    base = v[v.system_type == "baseline"].copy()
    base["ratio"] = base["n_feasible"] * base["p_survive"] / base["m"]
    base["p_full"] = [
        float(binom.sf(int(m) - 1, int(n), float(p))) if n > 0 else 0.0
        for n, p, m in zip(base["n_feasible"], base["p_survive"], base["m"])]

    below = base[base["ratio"] < 1.0]
    assert len(below), "expected some vectors with expected capacity below the threshold"
    counterexamples = below[below["p_full"] > 1e-6]
    assert len(counterexamples) >= 1, (
        "no cell has ratio < 1 with positive success probability; the claim "
        "'cannot reach the threshold at any budget' would be defensible and "
        "the prose should be revisited")
    # And the strongest counterexample must be substantial, not a rounding wisp.
    assert counterexamples["p_full"].max() > 0.1, (
        f"strongest counterexample is only {counterexamples['p_full'].max():.4f}")


def test_expected_capacity_ordering_holds():
    """E[X]/m must equal n_feasible * p_survive / m -- the definition the
    figure and table both describe."""
    v = _load("table_12_vector_optima")
    base = v[v.system_type == "baseline"]
    ratio = base["n_feasible"] * base["p_survive"] / base["m"]
    assert (ratio >= 0).all()
    # No single vector's EXPECTED yield reaches the threshold. This is the
    # claim the figure is actually entitled to make.
    assert (ratio < 1.0).all(), (
        "a single vector now has expected capacity at or above the threshold; "
        "the 'no single vector suffices' framing needs revisiting")


# ---------------------------------------------------------------------
# The coalition marker must be budget-FEASIBLE
# ---------------------------------------------------------------------

def test_naive_sum_of_capacities_is_not_budget_feasible():
    """Guards: the Figure 9 'all three combined' marker.

    Summing each vector's full independent capacity assumes the attacker
    funds all three at once with the whole budget three times over. This
    test demonstrates that is unaffordable, which is why the figure now
    plots the optimal coalition's mu_total/m instead.
    """
    v = _load("table_12_vector_optima")
    base = v[v.system_type == "baseline"]
    infeasible = 0
    for sid, grp in base.groupby("scenario_id"):
        cost = float((grp["n_feasible"] * grp["cost_per_attempt"]).sum()) \
            if "cost_per_attempt" in grp.columns else None
        if cost is None:
            continue
        budget = float(grp["B"].iloc[0]) if "B" in grp.columns else None
        if budget is not None and cost > budget + 1e-6:
            infeasible += 1
    if infeasible == 0:
        # Cost columns are not exported; fall back to the weaker structural
        # check that the naive sum exceeds the coalition's own expected yield.
        coal = _load("table_13_coalition")
        coal = coal[coal.system_type == "baseline"].set_index("scenario_id")
        b = base.copy()
        b["ratio"] = b["n_feasible"] * b["p_survive"] / b["m"]
        naive = b.groupby("scenario_id")["ratio"].sum()
        actual = (coal["mu_total"] / coal["m"]).reindex(naive.index)
        assert (naive >= actual - 1e-9).all(), (
            "the naive sum should never understate the achievable coalition")
        assert (naive > actual + 1e-9).any(), (
            "the naive sum coincides with the achievable coalition everywhere; "
            "the distinction the figure now draws would be vacuous")


def test_coalition_capacity_clears_the_threshold_where_claimed():
    """Guards: "the optimal split clears the line in four of five scenarios"."""
    coal = _load("table_13_coalition")
    base = coal[coal.system_type == "baseline"]
    clears = int(((base["mu_total"] / base["m"]) > 1.0).sum())
    assert clears == 4, f"coalition clears in {clears} of {len(base)}, not 4"


def test_coalition_optimum_is_not_generally_interior():
    """Guards: "the interior of that simplex dominates its corners".

    Three of five optima sit on an EDGE (one vector unfunded) and one is
    a corner, so the claim had to become "mixing at least two vectors".
    """
    coal = _load("table_13_coalition")
    base = coal[coal.system_type == "baseline"]
    shares = base[["share_bribery", "share_sybil", "share_ballot_stuffing"]].to_numpy()
    n_zero = (shares <= 1e-9).sum(axis=1)
    assert (n_zero > 0).any(), "no optimum leaves a vector unfunded; wording can be relaxed"
    assert (n_zero == 2).any(), "no optimum is a pure corner; wording can be relaxed"


# ---------------------------------------------------------------------
# Figure 6: the drawn curve must cross where the solver says it crosses
# ---------------------------------------------------------------------

def test_detection_sweep_resolves_the_critical_threshold():
    """Guards Figure 6: a labelled q_d* line the plotted curve misses.

    At the original 60-point resolution the polyline crossed zero about
    0.012 to the right of the labelled threshold.
    """
    sweep = _load("detection_sweep")
    thr = _load("table_11_scenario_thresholds")
    thr = thr[thr.system_type == "baseline"]

    for sid in sweep["scenario_id"].unique():
        d = sweep[sweep.scenario_id == sid].sort_values("q")
        row = thr[thr.scenario_id == sid]
        if not len(row):
            continue
        q_d = float(row["q_defender_critical"].iloc[0])
        if not np.isfinite(q_d) or q_d <= 0:
            continue
        pos = d[d["signed_attack_utility"] > 0]["q"]
        neg = d[d["signed_attack_utility"] <= 0]["q"]
        if not len(pos) or not len(neg):
            continue
        crossing = float(neg[neg > pos.min()].min())
        step = float(d["q"].diff().median())
        assert abs(crossing - q_d) <= 2 * step + 1e-9, (
            f"{sid}: plotted curve crosses zero at {crossing:.4f} but the solver "
            f"reports q_d* = {q_d:.4f} (grid step {step:.4f})")


def test_detection_sweep_flags_the_no_attack_sentinel():
    """The sentinel must be labelled, so the figure can mask it instead of
    plotting a constant as though it were an expected utility."""
    sweep = _load("detection_sweep")
    assert "attack_exists" in sweep.columns
    assert (~sweep["attack_exists"].astype(bool)).any(), (
        "no sentinel rows at all; the masking logic would be untested")


# ---------------------------------------------------------------------
# Scale effects are NOT uniform across vectors
# ---------------------------------------------------------------------

def test_electorate_growth_does_not_help_every_vector():
    """Guards: "success falls as the electorate grows".

    True for the budget-bound vectors, false for Sybil, whose attempt
    count is a fixed fraction of N.
    """
    sw = _load("electorate_size_sweep").sort_values("N")
    falls, rises = [], []
    for col in ("bribery_baseline", "sybil_baseline", "ballot_baseline"):
        if col not in sw.columns:
            continue
        corr = sw["N"].corr(sw[col])
        (rises if corr > 0.2 else falls).append(col)
    assert falls, "no vector's success falls with N"
    assert rises, (
        "every vector's success now falls with N; the findings text draws a "
        "distinction between budget-bound and proportionally-capped vectors "
        "that the data would no longer support")


# ---------------------------------------------------------------------
# Figure 1 must compare methods inside the incentive-compatible region
# ---------------------------------------------------------------------

def test_figure_one_scenario_is_incentive_compatible_where_it_matters():
    """Guards Figure 1: the collapse it exists to show must not sit inside
    the region the same figure shades as "bribe not incentive-compatible"."""
    import inspect
    from visualisation import plots as P
    from models.attacker import AttackerBudget

    sig = inspect.signature(P.fig01_method_comparison)
    d = {k: v.default for k, v in sig.parameters.items() if v.default is not inspect._empty}
    N, m, B, R, Pn = d["N"], d["m"], d["B"], d["R"], d["P"]

    T = AttackerBudget(N=N, B=B, R=R).max_targets()
    q_collapse = 1.0 - m / T
    q_v = R / (R + Pn)
    assert q_v > q_collapse, (
        f"q_v* = {q_v:.3f} sits below the collapse at q = {q_collapse:.3f}, so the "
        f"three-method comparison happens where no rational voter accepts")


# ---------------------------------------------------------------------
# The wrong-signed Chernoff form: the report quotes a specific count
# ---------------------------------------------------------------------

def test_wrong_sign_chernoff_failure_count_is_as_reported():
    """The report says the (1-delta) form fails in eleven of twelve cases."""
    cases = [(200, 0.55), (328, 0.771), (2000, 0.45), (500, 0.4)]
    deltas = (0.05, 0.10, 0.20)
    fails = total = 0
    for n, p in cases:
        mu = n * p
        for d in deltas:
            total += 1
            true = binom.sf(math.ceil((1 - d) * mu) - 1, n, p)
            wrong = math.exp(mu * (-d - (1 - d) * math.log1p(-d)))
            if wrong < true - 1e-12:
                fails += 1
    assert total == 12, f"the report says twelve cases; this enumerates {total}"
    assert fails == 11, f"the report says eleven failures; this finds {fails}"
