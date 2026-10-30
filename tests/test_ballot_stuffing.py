import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import numpy as np
from attacks.ballot_stuffing import run_ballot_stuffing_scenario


def test_ballot_basic_bounds():
    rng = np.random.default_rng(5)
    res = run_ballot_stuffing_scenario(N=1000, m=15, A=80, qb=0.4, pb=0.2, mc_trials=1000, rng=rng)
    assert 0 <= res.exact_probability_accepted_ge_m <= 1
    assert res.expected_accepted == 32.0


def test_ballot_full_detection():
    rng = np.random.default_rng(6)
    res = run_ballot_stuffing_scenario(N=1000, m=5, A=50, qb=0.5, pb=1.0, mc_trials=100, rng=rng)
    assert res.prob_all_escape_detection == 0.0
    assert res.expected_surviving == 0.0
