"""Tests for mathematics/thresholds.py (T1-T7)."""

import sys
import os
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mathematics.thresholds import (
    incentive_reward_threshold,
    voter_indifference_detection,
    min_attempts_for_confidence,
    attacker_break_even_budget,
    defender_critical_detection,
    chernoff_certified_margin,
    attacker_reachable_margin,
    best_attacking_utility,
)
from mathematics.binomial import p_at_least
from mathematics.chernoff import chernoff_bound_for_threshold
from mathematics.utility import voter_utility


# --- T1 / T2 -----------------------------------------------------------

def test_incentive_reward_threshold_matches_m2():
    q, P = 0.2, 500.0
    t = incentive_reward_threshold(q, P)
    assert t.exists
    assert math.isclose(t.value, q * P / (1 - q))
    # Just above the threshold the voter accepts, just below refuses.
    assert voter_utility(q, t.value * 1.001, P) > 0
    assert voter_utility(q, t.value * 0.999, P) < 0


def test_incentive_reward_threshold_undefined_at_certain_detection():
    t = incentive_reward_threshold(1.0, 500.0)
    assert not t.exists and t.value is None


def test_voter_indifference_detection_zeroes_utility():
    R, P = 200.0, 800.0
    t = voter_indifference_detection(R, P)
    assert t.exists
    assert math.isclose(t.value, R / (R + P))
    assert math.isclose(voter_utility(t.value, R, P), 0.0, abs_tol=1e-9)
    assert voter_utility(t.value - 0.01, R, P) > 0   # below: accept
    assert voter_utility(t.value + 0.01, R, P) < 0   # above: refuse


def test_voter_indifference_is_upper_bound_on_useful_detection():
    """No bribe is accepted above q_v*, whatever the budget."""
    R, P = 100.0, 100.0
    t = voter_indifference_detection(R, P)
    assert math.isclose(t.value, 0.5)


# --- T3 ----------------------------------------------------------------

def test_min_attempts_is_minimal_and_sufficient():
    p, m, alpha = 0.6, 50, 0.5
    t = min_attempts_for_confidence(p, m, alpha)
    assert t.exists
    n = int(t.value)
    assert p_at_least(n, p, m) >= alpha
    assert p_at_least(n - 1, p, m) < alpha


def test_min_attempts_none_when_unreachable():
    t = min_attempts_for_confidence(0.0, 10, 0.5)
    assert not t.exists and t.value is None


def test_min_attempts_zero_for_nonpositive_threshold():
    t = min_attempts_for_confidence(0.5, 0, 0.5)
    assert t.exists and t.value == 0.0


# --- T4 / T5 -----------------------------------------------------------

def test_break_even_budget_brackets_profitability():
    N, m, R, P, q = 1000, 120, 50.0, 400.0, 0.05
    V, D = 500_000.0, 20_000.0
    t = attacker_break_even_budget(N, m, R, P, q, V, D)
    assert t.exists
    below = best_attacking_utility(N, m, t.value * 0.9, R, P, q, V, D)
    above = best_attacking_utility(N, m, t.value * 1.1, R, P, q, V, D)
    assert below <= 0 < above


def test_best_attacking_utility_can_be_negative():
    """Unlike the headline optimiser (which may always decline), the
    signed utility of actually attacking must be able to go negative."""
    u = best_attacking_utility(N=1000, m=900, B=100_000.0, R=50.0, P=400.0,
                               q=0.05, V=1_000.0, D_attack=500_000.0)
    assert u < 0


def test_break_even_budget_absent_when_bribe_not_incentive_compatible():
    # q above q_v* = R/(R+P) = 0.1 -> voters refuse at any budget.
    t = attacker_break_even_budget(N=1000, m=100, R=50.0, P=450.0, q=0.5,
                                   V=1e6, D_attack=1e4)
    assert not t.exists


def test_critical_detection_kills_attacker_utility():
    N, m, B, R, P = 2000, 200, 400_000.0, 100.0, 900.0
    V, D = 4_000_000.0, 250_000.0
    t = defender_critical_detection(N, m, B, R, P, V, D)
    assert t.exists
    assert best_attacking_utility(N, m, B, R, P, t.value + 1e-4, V, D) <= 0
    if t.value > 1e-3:
        assert best_attacking_utility(N, m, B, R, P, t.value - 1e-4, V, D) > 0


def test_critical_detection_never_exceeds_voter_indifference():
    R, P = 100.0, 900.0
    t = defender_critical_detection(N=2000, m=200, B=400_000.0, R=R, P=P,
                                    V=4_000_000.0, D_attack=250_000.0)
    q_v = voter_indifference_detection(R, P)
    assert t.exists and t.value <= q_v.value + 1e-6


# --- T6 / T7 -----------------------------------------------------------

def test_certified_margin_is_minimal_and_certified():
    n, p, eps = 500, 0.4, 1e-3
    t = chernoff_certified_margin(n, p, eps)
    assert t.exists
    m = int(t.value)
    assert (chernoff_bound_for_threshold(n, p, m).bound or 1.0) <= eps
    assert (chernoff_bound_for_threshold(n, p, m - 1).bound or 1.0) > eps


def test_certified_margin_is_conservative_versus_exact():
    """The certified margin must be at least as large as the exact
    margin at the same epsilon -- the bound never under-states risk."""
    n, p, eps = 500, 0.4, 1e-3
    t = chernoff_certified_margin(n, p, eps)
    assert p_at_least(n, p, int(t.value)) <= eps


def test_reachable_margin_brackets_alpha():
    n, p, alpha = 800, 0.5, 0.5
    t = attacker_reachable_margin(n, p, alpha)
    assert t.exists
    m = int(t.value)
    assert p_at_least(n, p, m) >= alpha
    assert p_at_least(n, p, m + 1) < alpha


def test_reachable_margin_below_certified_margin():
    """The contested band is well-ordered: m_alpha < m_eps."""
    n, p = 800, 0.5
    reachable = attacker_reachable_margin(n, p, 0.5)
    certified = chernoff_certified_margin(n, p, 1e-3)
    assert reachable.value < certified.value


def test_threshold_annotation_strings():
    t = voter_indifference_detection(200.0, 800.0)
    assert t.annotation().startswith("q_v* = 0.2")
    missing = incentive_reward_threshold(1.0, 100.0)
    assert "does not exist" in missing.annotation()
