import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from simulation.named_scenarios import run_named_scenarios, SCENARIOS


def test_five_scenarios_defined():
    assert len(SCENARIOS) == 5
    ids = [s.scenario_id for s in SCENARIOS]
    assert ids == ["S1", "S2", "S3", "S4", "S5"]


def test_low_budget_scenario_fails():
    df = run_named_scenarios(mc_trials=2000, seed=1)
    s5 = df[(df.scenario_id == "S5") & (df.system_type == "baseline")].iloc[0]
    assert s5["exact_probability"] < 0.01


def test_protected_suppresses_all_scenarios():
    df = run_named_scenarios(mc_trials=2000, seed=1)
    protected = df[df.system_type == "protected"]
    assert (protected["exact_probability"] < 0.01).all()


def test_reproducible_with_same_seed():
    df1 = run_named_scenarios(mc_trials=2000, seed=5)
    df2 = run_named_scenarios(mc_trials=2000, seed=5)
    assert df1["monte_carlo_probability"].tolist() == df2["monte_carlo_probability"].tolist()


def test_chernoff_bound_holds_where_defined():
    df = run_named_scenarios(mc_trials=2000, seed=1)
    valid = df[df.chernoff_bound.notna()]
    assert (valid["chernoff_bound"] >= valid["exact_probability"] - 1e-9).all()
