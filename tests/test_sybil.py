import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import numpy as np
from attacks.sybil import run_sybil_scenario


def test_sybil_basic_bounds():
    rng = np.random.default_rng(3)
    res = run_sybil_scenario(N=1000, m=20, S=100, qs=0.5, pd=0.1, mc_trials=1000, rng=rng)
    assert 0 <= res.exact_probability_accepted_ge_m <= 1
    assert 0 <= res.prob_at_least_one_detected <= 1
    assert res.expected_accepted == 50.0


def test_sybil_zero_attempts():
    rng = np.random.default_rng(4)
    res = run_sybil_scenario(N=1000, m=5, S=0, qs=0.5, pd=0.1, mc_trials=100, rng=rng)
    assert res.expected_accepted == 0.0
    assert res.exact_probability_accepted_ge_m == 0.0
