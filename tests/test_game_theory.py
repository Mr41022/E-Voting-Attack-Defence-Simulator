"""Tests for attacks/game_theory.py (G1 unified optimal effort, G2 coalition)."""

import sys
import os
import math

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from attacks.game_theory import (
    VectorSpec,
    bribery_spec,
    sybil_spec,
    ballot_stuffing_spec,
    vector_utility,
    optimal_effort,
    coalition_attack,
    optimal_coalition,
)
from attacks.bribery_game_theory import optimal_attempts
from mathematics.binomial import p_at_least


# --- G1: feasibility and gates ----------------------------------------

def test_feasible_attempts_respects_budget_and_ceiling():
    spec = VectorSpec("test", unit_cost=100.0, p_survive=0.5, p_detect=0.1, n_ceiling=30)
    assert spec.feasible_attempts(1000.0) == 10      # budget-bound
    assert spec.feasible_attempts(10_000.0) == 30    # ceiling-bound
    assert spec.feasible_attempts(0.0) == 0
    assert spec.feasible_attempts(99.0) == 0         # cannot afford one attempt


def test_zero_unit_cost_yields_zero_attempts_not_division_error():
    spec = VectorSpec("test", unit_cost=0.0, p_survive=0.5, p_detect=0.1, n_ceiling=30)
    assert spec.feasible_attempts(1000.0) == 0


def test_bribery_gate_closed_above_voter_indifference():
    # q_v* = R/(R+P) = 100/1100 ~= 0.0909
    spec, gate = bribery_spec(R=100.0, P=1000.0, q=0.5, N=1000)
    assert gate is False
    result = optimal_effort(spec, m=50, budget=1e6, V=1e7, D_attack=1e5, gate_open=gate)
    assert result.n_star == 0 and result.utility_star == 0.0 and not result.viable


def test_bribery_gate_open_below_voter_indifference():
    spec, gate = bribery_spec(R=100.0, P=1000.0, q=0.02, N=1000)
    assert gate is True
    assert math.isclose(spec.p_survive, 0.98)


def test_sybil_and_ballot_survival_probabilities():
    s = sybil_spec(cost_per_identity=20.0, qs=0.8, pd=0.25, registration_ceiling=500)
    assert math.isclose(s.p_survive, 0.8 * 0.75)
    b = ballot_stuffing_spec(cost_per_ballot=5.0, qb=0.6, pb=0.4, submission_ceiling=900)
    assert math.isclose(b.p_survive, 0.6 * 0.6)


# --- G1: utility and optimum ------------------------------------------

def test_utility_formula_matches_components():
    spec = VectorSpec("test", unit_cost=10.0, p_survive=0.5, p_detect=0.05, n_ceiling=1000)
    pt = vector_utility(spec, n=100, m=60, V=100_000.0, D_attack=5_000.0)
    expected_p = p_at_least(100, 0.5, 60)
    expected_noticed = 1 - (1 - 0.05) ** 100
    assert math.isclose(pt.p_success, expected_p, rel_tol=1e-12)
    assert math.isclose(pt.cost, 1000.0)
    assert math.isclose(pt.p_noticed, expected_noticed, rel_tol=1e-9)
    assert math.isclose(pt.utility,
                        expected_p * 100_000.0 - 1000.0 - expected_noticed * 5_000.0,
                        rel_tol=1e-9)


def test_optimal_effort_is_best_point_on_its_own_curve():
    spec = VectorSpec("test", unit_cost=50.0, p_survive=0.7, p_detect=0.02, n_ceiling=400)
    res = optimal_effort(spec, m=120, budget=20_000.0, V=500_000.0, D_attack=30_000.0)
    assert res.utility_star >= max(pt.utility for pt in res.curve) - 1e-9


def test_optimal_effort_never_below_doing_nothing():
    """A rational attacker can always decline: U(n*) >= 0."""
    spec = VectorSpec("test", unit_cost=500.0, p_survive=0.3, p_detect=0.4, n_ceiling=200)
    res = optimal_effort(spec, m=150, budget=100_000.0, V=1_000.0, D_attack=90_000.0)
    assert res.utility_star >= 0.0
    assert res.n_star == 0 and not res.viable


def test_unified_bribery_agrees_with_dedicated_bribery_module():
    """G1 applied to bribery must reproduce the original bribery-only
    optimiser's utility at its own T* (same model, one interface)."""
    N, m, B, R, P, q = 500, 60, 60_000.0, 100.0, 900.0, 0.03
    V, D = 800_000.0, 50_000.0
    legacy = optimal_attempts(N, m, B, R, P, q, V, D)
    spec, gate = bribery_spec(R, P, q, N)
    unified = vector_utility(spec, legacy.T_star, m, V, D, gate)
    assert math.isclose(unified.utility, legacy.utility_star, rel_tol=1e-9)


# --- G2: coalition ----------------------------------------------------

def _three_specs():
    b, gate = bribery_spec(R=100.0, P=2000.0, q=0.03, N=2000)
    s = sybil_spec(cost_per_identity=40.0, qs=0.7, pd=0.10, registration_ceiling=2000)
    z = ballot_stuffing_spec(cost_per_ballot=15.0, qb=0.6, pb=0.15, submission_ceiling=2000)
    return [b, s, z], {"bribery": gate}


def test_coalition_exact_matches_monte_carlo():
    """The convolution-based exact P(W_total >= m) must agree with a
    direct Monte Carlo simulation of the same three binomials."""
    specs, gates = _three_specs()
    m, budget = 90, 30_000.0
    res = coalition_attack(specs, m, budget, (1 / 3, 1 / 3, 1 / 3), V=1e6,
                           D_attack=1e5, gate_open=gates)
    rng = np.random.default_rng(7)
    draws = np.zeros(200_000, dtype=int)
    for spec in specs:
        n = res.attempts[spec.name]
        if n > 0:
            draws += rng.binomial(n, spec.p_survive, size=200_000)
    mc = float(np.mean(draws >= m))
    assert abs(res.exact_p_success - mc) < 0.01


def test_coalition_mean_is_sum_of_component_means():
    specs, gates = _three_specs()
    res = coalition_attack(specs, 90, 30_000.0, (0.5, 0.3, 0.2), 1e6, 1e5, gates)
    assert math.isclose(res.mu_total, sum(res.expected_surviving.values()), rel_tol=1e-12)


def test_coalition_chernoff_bound_holds():
    specs, gates = _three_specs()
    for shares in [(1, 0, 0), (0, 1, 0), (0, 0, 1), (0.4, 0.4, 0.2), (0.2, 0.3, 0.5)]:
        res = coalition_attack(specs, 200, 40_000.0, shares, 1e6, 1e5, gates)
        if res.chernoff_bound is not None:
            assert res.chernoff_bound >= res.exact_p_success - 1e-12


def test_coalition_budget_shares_normalise():
    specs, gates = _three_specs()
    res = coalition_attack(specs, 90, 30_000.0, (2, 2, 4), 1e6, 1e5, gates)
    assert math.isclose(sum(res.allocation.values()), 1.0, rel_tol=1e-12)
    assert math.isclose(res.allocation["ballot_stuffing"], 0.5, rel_tol=1e-12)


def test_coalition_never_exceeds_budget():
    specs, gates = _three_specs()
    budget = 30_000.0
    _, grid = optimal_coalition(specs, 90, budget, 1e6, 1e5, gates, grid_step=0.25)
    for res in grid:
        assert res.total_cost <= budget + 1e-6


def test_optimal_coalition_beats_or_matches_every_single_vector():
    """A pure single-vector strategy is a corner of the simplex, so the
    optimal mixed strategy can never be worse than the best pure one."""
    specs, gates = _three_specs()
    m, budget, V, D = 120, 40_000.0, 2_000_000.0, 150_000.0
    best, _ = optimal_coalition(specs, m, budget, V, D, gates, grid_step=0.05)
    pure = []
    for i, spec in enumerate(specs):
        shares = [0.0, 0.0, 0.0]
        shares[i] = 1.0
        pure.append(coalition_attack(specs, m, budget, shares, V, D, gates).utility)
    assert best.utility >= max(pure) - 1e-6


def test_closed_bribery_gate_removes_that_vector_from_the_coalition():
    specs, _ = _three_specs()
    res = coalition_attack(specs, 90, 30_000.0, (1 / 3, 1 / 3, 1 / 3), 1e6, 1e5,
                           gate_open={"bribery": False})
    assert res.attempts["bribery"] == 0
    assert res.attempts["sybil"] > 0
