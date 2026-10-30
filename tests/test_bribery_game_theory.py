import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from attacks.bribery_game_theory import optimal_attempts, attacker_utility


def test_zero_budget_gives_zero_attempts():
    res = optimal_attempts(N=1000, m=100, B=0, R=100, P=500, q=0.1, V=100000, D_attack=5000)
    assert res.T_star == 0
    assert res.utility_star == 0.0


def test_voter_rejection_forces_zero_attempts_regardless_of_budget():
    # Very high detection + penalty -> Uv <= 0 -> rational rejection
    res = optimal_attempts(N=2000, m=250, B=10_000_000, R=50, P=50000, q=0.6, V=500000, D_attack=20000)
    assert res.voter_accepts is False
    assert res.T_star == 0


def test_low_budget_produces_near_zero_flip_probability():
    res = optimal_attempts(N=5000, m=600, B=2000, R=150, P=800, q=0.1, V=500000, D_attack=20000)
    assert res.p_flip_at_T_star < 0.05


def test_interior_optimum_found_for_reasonable_scenario():
    res = optimal_attempts(N=2000, m=250, B=100000, R=150, P=800, q=0.15, V=500000, D_attack=20000)
    assert 0 < res.T_star < res.T_max_feasible
    assert res.utility_star > 0


def test_utility_never_exceeds_reward_alone():
    pt = attacker_utility(T=100, m=50, q=0.1, R=100, V=100000, D_attack=5000, voter_accepts=True)
    assert pt.utility <= 100000


def test_curve_is_monotonic_length_and_includes_endpoints():
    res = optimal_attempts(N=3000, m=300, B=50000, R=100, P=500, q=0.1, V=200000, D_attack=10000)
    Ts = [pt.T for pt in res.curve]
    assert Ts[0] == 0
    assert Ts[-1] == res.T_max_feasible
