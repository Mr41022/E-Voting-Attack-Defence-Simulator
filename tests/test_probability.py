import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import math
from mathematics.binomial import p_at_least, expected_value, validate_binomial_params
from mathematics.probability import prob_at_least_one_detected, prob_all_escape_detection


def test_expected_value():
    assert expected_value(100, 0.3) == 30.0


def test_p_at_least_m_le_zero():
    assert p_at_least(50, 0.3, 0) == 1.0
    assert p_at_least(50, 0.3, -5) == 1.0


def test_p_at_least_m_gt_n():
    assert p_at_least(50, 0.3, 51) == 0.0


def test_p_at_least_matches_known_value():
    # Binomial(10, 0.5), P(X>=5) known ~ 0.623046875
    val = p_at_least(10, 0.5, 5)
    assert math.isclose(val, 0.623046875, rel_tol=1e-6)


def test_detection_complement():
    n, pd = 20, 0.1
    a = prob_at_least_one_detected(n, pd)
    b = prob_all_escape_detection(n, pd)
    assert math.isclose(a + b, 1.0, rel_tol=1e-9)


def test_detection_edge_cases():
    assert prob_at_least_one_detected(0, 0.5) == 0.0
    assert prob_all_escape_detection(0, 0.5) == 1.0
    assert prob_at_least_one_detected(10, 1.0) == 1.0
    assert prob_all_escape_detection(10, 1.0) == 0.0


def test_validate_binomial_params_clamps():
    n, p = validate_binomial_params(-5, 1.5)
    assert n == 0
    assert p == 1.0
