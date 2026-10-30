"""Independent audit verification script (does not modify project files)."""
import math
import sys

try:
    import numpy as np
except ImportError:
    class _FallbackRandomGenerator: 
        def __init__(self, seed=None):
            import random
            self._rng = random.Random(seed)

        def integers(self, low, high=None):
            if high is None:
                high = low
                low = 0
            return self._rng.randrange(low, high)

        def uniform(self, low=0.0, high=1.0):
            return self._rng.uniform(low, high)

    class _FallbackNumpyRandom:
        @staticmethod
        def default_rng(seed=None):
            return _FallbackRandomGenerator(seed)

    class _FallbackNumpy:
        random = _FallbackNumpyRandom
        inf = float("inf")

    np = _FallbackNumpy()

try:
    from scipy.stats import binom
except ImportError:
    class _FallbackBinom:
        @staticmethod
        def cdf(k, n, p):
            k = int(k)
            n = int(n)
            p = float(p)
            total = 0.0
            for i in range(k + 1):
                total += math.comb(n, i) * (p ** i) * ((1.0 - p) ** (n - i))
            return total

    binom = _FallbackBinom()

sys.path.insert(0, ".")
from mathematics.utility import voter_utility, rational_voter_decision, incentive_threshold
from mathematics.binomial import p_at_least, expected_value
from mathematics.chernoff import chernoff_upper_tail, chernoff_lower_tail, chernoff_certificate
from models.attacker import AttackerBudget
from mathematics.probability import prob_all_escape_detection

print("=== M1/M2 utility edge cases ===")
for q, R, P in [(0, 100, 50), (1, 100, 50), (0.5, 0, 50), (0.5, 100, 0), (0.5, 100, 200)]:
    d = rational_voter_decision(q, R, P)
    print(f"q={q} R={R} P={P}: Uv={d.Uv}, accepts={d.accepts}, thresh={d.incentive_threshold}")

print("\n=== M3 budget ===")
for N, B, R in [(1000, 50000, 100), (100, 50000, 100), (1000, 0, 100),
                (1000, 5000, 0), (1000, 50, 100)]:
    print(f"N={N} B={B} R={R}: T={AttackerBudget(N,B,R).max_targets()}")

print("\n=== M5 exact binomial edges ===")
print("p_at_least(10, 0.5, 0) =", p_at_least(10, 0.5, 0))
print("p_at_least(10, 0.5, 11)=", p_at_least(10, 0.5, 11))
print("p_at_least(0, 0.7, 1) =", p_at_least(0, 0.7, 1))
print("p_at_least(4, 1.0, 4) =", p_at_least(4, 1.0, 4))

print("\n=== Chernoff validity checks ===")
bad = 0
for n in [50, 200, 1000]:
    for p in [0.2, 0.4, 0.6]:
        mu = n * p
        for m in range(int(mu) + 2, n + 1):
            r = chernoff_upper_tail(mu, m)
            if r.bound is not None:
                true = p_at_least(n, p, m)
                if r.bound < true - 1e-12:
                    bad += 1
                    print(f"VIOLATION upper: n={n} p={p} m={m} bound={r.bound:.6g} true={true:.6g}")
print(f"upper-tail violations: {bad}")

badl = 0
for n in [50, 200, 1000]:
    for p in [0.4, 0.6, 0.8]:
        mu = n * p
        for m in range(1, int(mu) - 1):
            r = chernoff_lower_tail(mu, m)
            if r.bound is not None:
                true = binom.cdf(m, n, p)
                if r.bound < true - 1e-9:
                    badl += 1
                    print(f"VIOLATION lower: n={n} p={p} m={m} bound={r.bound:.6g} true={true:.6g}")
print(f"lower-tail violations: {badl}")

print("\n=== Certificate containment sweep ===")
viol = 0; total = 0
rng = np.random.default_rng(0)
for _ in range(3000):
    n = int(rng.integers(20, 800)); p = float(rng.uniform(0.05, 0.95))
    m = int(rng.integers(1, n + 1))
    c = chernoff_certificate(n, p, m)
    exact = p_at_least(n, p, m)
    total += 1
    lo = c.p_success_lower if c.p_success_lower is not None else -np.inf
    hi = c.p_success_upper if c.p_success_upper is not None else np.inf
    if not (lo <= exact + 1e-9 and exact <= hi + 1e-9):
        viol += 1
        print(f"CERT VIOLATION n={n} p={p} m={m} dir={c.direction} [{lo},{hi}] exact={exact}")
print(f"certificate containment violations: {viol}/{total}")

print("\n=== Detection survival sanity ===")
print("(1-p)^S S=10 p=0.3:", prob_all_escape_detection(10, 0.3), "expect", 0.7**10)
