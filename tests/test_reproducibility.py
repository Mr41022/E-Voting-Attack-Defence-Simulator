import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from simulation.experiment_runner import run_all_trials


def test_reproducibility_same_seed():
    r1 = run_all_trials(n_trials=5, seed=42, mc_trials=200)
    r2 = run_all_trials(n_trials=5, seed=42, mc_trials=200)
    assert r1["bribery"]["monte_carlo_probability"].tolist() == r2["bribery"]["monte_carlo_probability"].tolist()
    assert r1["sybil"]["exact_probability_accepted_ge_m"].tolist() == r2["sybil"]["exact_probability_accepted_ge_m"].tolist()


def test_different_seed_differs():
    r1 = run_all_trials(n_trials=5, seed=42, mc_trials=200)
    r3 = run_all_trials(n_trials=5, seed=43, mc_trials=200)
    assert r1["bribery"]["N"].tolist() != r3["bribery"]["N"].tolist()
