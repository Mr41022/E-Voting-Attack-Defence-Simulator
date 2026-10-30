import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import numpy as np
from attacks.bribery import run_bribery_scenario
from mathematics.utility import voter_utility, rational_voter_decision


def test_voter_rejects_when_high_detection_high_penalty():
    d = rational_voter_decision(q=0.9, R=50, P=5000)
    assert d.accepts is False


def test_voter_accepts_when_low_detection_high_reward():
    d = rational_voter_decision(q=0.05, R=1000, P=100)
    assert d.accepts is True


def test_bribery_scenario_zero_budget():
    rng = np.random.default_rng(1)
    res = run_bribery_scenario(N=1000, m=50, B=0, R=100, P=500, q=0.1,
                                mc_trials=500, rng=rng)
    assert res.T == 0
    assert res.bribes_accepted == 0
    assert res.exact_probability == 0.0  # m>0, T effectively 0


def test_bribery_scenario_voters_reject_yields_zero_success():
    rng = np.random.default_rng(2)
    # extremely high penalty & detection -> should reject
    res = run_bribery_scenario(N=1000, m=10, B=100000, R=50, P=100000, q=0.5,
                                mc_trials=500, rng=rng)
    assert res.voter_decision == "reject"
    assert res.bribes_accepted == 0
    assert res.exact_probability == 0.0


def test_bribery_reproducibility():
    rng1 = np.random.default_rng(7)
    rng2 = np.random.default_rng(7)
    r1 = run_bribery_scenario(500, 20, 20000, 100, 200, 0.1, 1000, rng1)
    r2 = run_bribery_scenario(500, 20, 20000, 100, 200, 0.1, 1000, rng2)
    assert r1.monte_carlo_probability == r2.monte_carlo_probability
