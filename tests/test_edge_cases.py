import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import math
from mathematics.binomial import p_at_least, expected_value
from mathematics.utility import voter_utility, incentive_threshold
from models.attacker import AttackerBudget


def test_m_le_zero():
    assert p_at_least(100, 0.5, 0) == 1.0


def test_m_gt_N_via_attacker_budget_zero_T():
    ab = AttackerBudget(N=100, B=0, R=50)
    assert ab.max_targets() == 0


def test_B_lt_R():
    ab = AttackerBudget(N=100, B=10, R=50)
    assert ab.max_targets() == 0


def test_R_zero():
    ab = AttackerBudget(N=100, B=1000, R=0)
    assert ab.max_targets() == 0


def test_q_zero_and_one():
    assert expected_value(50, 0) == 0.0
    assert expected_value(50, 1) == 50.0


def test_incentive_threshold_q_equals_one_is_none():
    assert incentive_threshold(1.0, 500) is None


def test_penalty_zero():
    Uv = voter_utility(q=0.5, R=100, P=0)
    assert Uv == 50.0


def test_large_N_no_overflow():
    val = p_at_least(2_000_000, 0.001, 100)
    assert 0 <= val <= 1
    assert not math.isnan(val)
