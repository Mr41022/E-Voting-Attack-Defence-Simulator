"""
attacks/game_theory.py

UNIFIED RATIONAL-ATTACKER LAYER (thesis extension G1-G2).

attacks/bribery_game_theory.py answers the optimal-strategy question
for bribery only. Real attackers are not restricted to one vector, and
a security evaluation that optimises the defender against bribery
while leaving Sybil registration and ballot stuffing un-modelled at the
strategic level is incomplete. This module generalises the
expected-utility search to all three vectors under one interface, and
adds the combined (coalition) attack in which a single budget is split
across vectors simultaneously.

Common structure. Every vector is a sequence of independent, identical
attempts. One attempt costs the attacker `unit_cost`, yields a
fraudulent vote that survives all countermeasures with probability
`p_survive`, and is independently flagged by the audit machinery with
probability `p_detect`. For n attempts:

    W  ~ Binomial(n, p_survive)                    surviving fraud votes
    P(attack noticed at all) = 1 - (1 - p_detect)^n            (M11/M14)
    U(n) = P(W >= m) * V  -  n * unit_cost  -  P(noticed) * D  (G1)

Bribery additionally carries the rational-voter gate of M1: if
Uv = (1-q)R - qP <= 0 the targeted voters refuse, no attempt
materialises, and U(n) = 0 for every n. That gate is why the bribery
utility curve can be identically zero while the Sybil curve for the
same budget is not.

Coalition attack (G2). With budget shares (w_bribery, w_sybil,
w_ballot) summing to one, the surviving fraudulent votes are

    W_total = W_bribery + W_sybil + W_ballot                    (G2)

a sum of independent binomials with *different* success probabilities,
which is not itself binomial. Its exact distribution is obtained here
by convolving the three probability mass functions -- no normal or
Poisson approximation is used -- so P(W_total >= m) is exact up to
floating-point. The Chernoff bound still applies unchanged, because
W_total is a sum of independent Bernoulli variables and the bound is
stated for exactly that class; mu is simply the sum of the three
component means.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import math
import numpy as np
from scipy.stats import binom

from mathematics.binomial import p_at_least, expected_value
from mathematics.chernoff import chernoff_bound_for_threshold, chernoff_upper_tail
from mathematics.probability import prob_at_least_one_detected
from mathematics.utility import rational_voter_decision


# ---------------------------------------------------------------------
# G1 -- one vector, optimal effort
# ---------------------------------------------------------------------

@dataclass
class VectorSpec:
    """One attack vector, expressed in the common attempt/survive/detect
    form so the three vectors can be compared and combined.

    name        vector label ("bribery", "sybil", "ballot_stuffing")
    unit_cost   attacker cost of one attempt
    p_survive   probability one attempt becomes a counted fraudulent vote
    p_detect    probability one attempt is independently flagged
    n_ceiling   structural cap on attempts (electorate size, registration
                capacity, ballot-submission capacity)
    """
    name: str
    unit_cost: float
    p_survive: float
    p_detect: float
    n_ceiling: int

    def feasible_attempts(self, budget: float) -> int:
        """Largest number of attempts affordable within `budget`, capped
        by the structural ceiling. Mirrors M3's convention: a zero or
        negative unit cost, budget or ceiling all yield zero attempts
        rather than an undefined division.
        """
        if self.unit_cost <= 0 or budget <= 0 or self.n_ceiling <= 0:
            return 0
        return int(max(0, min(self.n_ceiling, math.floor(budget / self.unit_cost))))


@dataclass
class EffortPoint:
    n: int
    p_success: float
    cost: float
    p_noticed: float
    expected_penalty: float
    utility: float


@dataclass
class OptimalEffort:
    vector: str
    n_feasible: int
    n_star: int
    utility_star: float
    p_success_at_star: float
    cost_at_star: float
    viable: bool               # is the best achievable utility strictly positive?
    gate_open: bool            # bribery only: did voters accept?
    curve: List[EffortPoint] = field(default_factory=list)


def vector_utility(spec: VectorSpec, n: int, m: int, V: float, D_attack: float,
                   gate_open: bool = True) -> EffortPoint:
    """G1: U(n) = P(W >= m)*V - n*unit_cost - P(noticed)*D_attack."""
    if n <= 0 or not gate_open:
        return EffortPoint(n=max(0, n), p_success=0.0, cost=0.0, p_noticed=0.0,
                           expected_penalty=0.0, utility=0.0)
    p_success = p_at_least(n, spec.p_survive, m)
    cost = n * spec.unit_cost
    p_noticed = prob_at_least_one_detected(n, spec.p_detect)
    penalty = p_noticed * D_attack
    return EffortPoint(n=n, p_success=p_success, cost=cost, p_noticed=p_noticed,
                       expected_penalty=penalty, utility=p_success * V - cost - penalty)


def optimal_effort(spec: VectorSpec, m: int, budget: float, V: float,
                   D_attack: float, gate_open: bool = True,
                   grid_points: int = 120) -> OptimalEffort:
    """Search n in [0, feasible] for the utility-maximising effort.

    The utility curve is evaluated on a grid when the feasible range is
    large (it is smooth in n, and the grid always includes both
    endpoints), then refined by a local exhaustive sweep around the
    grid winner so the reported n* is exact to within one attempt
    rather than to within one grid step.
    """
    n_feasible = spec.feasible_attempts(budget)
    if n_feasible <= 0 or not gate_open:
        zero = vector_utility(spec, 0, m, V, D_attack, gate_open)
        return OptimalEffort(vector=spec.name, n_feasible=n_feasible, n_star=0,
                             utility_star=0.0, p_success_at_star=0.0, cost_at_star=0.0,
                             viable=False, gate_open=gate_open, curve=[zero])

    if n_feasible <= grid_points:
        candidates = list(range(0, n_feasible + 1))
    else:
        candidates = sorted(set([0] + list(np.linspace(1, n_feasible, grid_points, dtype=int))
                                + [n_feasible]))

    curve = [vector_utility(spec, n, m, V, D_attack, gate_open) for n in candidates]
    best = max(curve, key=lambda pt: pt.utility)

    # Local refinement around the grid winner.
    if n_feasible > grid_points:
        step = max(1, n_feasible // grid_points)
        lo = max(0, best.n - step)
        hi = min(n_feasible, best.n + step)
        fine = max(1, (hi - lo) // 60)
        for n in range(lo, hi + 1, fine):
            pt = vector_utility(spec, n, m, V, D_attack, gate_open)
            if pt.utility > best.utility:
                best = pt

    return OptimalEffort(vector=spec.name, n_feasible=n_feasible, n_star=best.n,
                         utility_star=best.utility, p_success_at_star=best.p_success,
                         cost_at_star=best.cost, viable=best.utility > 0,
                         gate_open=gate_open, curve=curve)


def bribery_spec(R: float, P: float, q: float, N: int) -> Tuple[VectorSpec, bool]:
    """Build the bribery VectorSpec and evaluate the M1 rational-voter
    gate. Returns (spec, gate_open).

    Under this project's convention q is the DETECTION probability, so a
    bribed vote survives with probability 1-q and the same q drives the
    per-attempt detection term.
    """
    q = min(1.0, max(0.0, q))
    spec = VectorSpec(name="bribery", unit_cost=R, p_survive=1.0 - q,
                      p_detect=q, n_ceiling=N)
    return spec, rational_voter_decision(q, R, P).accepts


def sybil_spec(cost_per_identity: float, qs: float, pd: float,
               registration_ceiling: int) -> VectorSpec:
    """Sybil vector. A forged identity must both pass registration
    (probability qs) and escape detection (probability 1-pd) to place a
    counted vote, so p_survive = qs(1-pd) -- the same independence
    assumption already documented for M11 in ASSUMPTIONS.md.
    """
    qs = min(1.0, max(0.0, qs))
    pd = min(1.0, max(0.0, pd))
    return VectorSpec(name="sybil", unit_cost=cost_per_identity,
                      p_survive=qs * (1.0 - pd), p_detect=pd,
                      n_ceiling=registration_ceiling)


def ballot_stuffing_spec(cost_per_ballot: float, qb: float, pb: float,
                         submission_ceiling: int) -> VectorSpec:
    """Ballot-stuffing vector, p_survive = qb(1-pb) by the M14 analogue."""
    qb = min(1.0, max(0.0, qb))
    pb = min(1.0, max(0.0, pb))
    return VectorSpec(name="ballot_stuffing", unit_cost=cost_per_ballot,
                      p_survive=qb * (1.0 - pb), p_detect=pb,
                      n_ceiling=submission_ceiling)


# ---------------------------------------------------------------------
# G2 -- coalition (multi-vector) attack
# ---------------------------------------------------------------------

def _binomial_pmf_vector(n: int, p: float, k_max: int) -> np.ndarray:
    """PMF of Binomial(n,p) restricted to 0..k_max, as a dense vector.

    Mass above k_max is DROPPED, not folded into the top cell. That is
    what makes the truncated convolution below exact: the coefficient of
    k in the convolution of truncated PMFs equals P(sum = k) exactly for
    every k <= k_max, because no combination summing to k can involve a
    component larger than k.
    """
    if n <= 0 or p <= 0:
        v = np.zeros(k_max + 1)
        v[0] = 1.0
        return v
    ks = np.arange(0, min(n, k_max) + 1)
    out = np.zeros(k_max + 1)
    out[: len(ks)] = binom.pmf(ks, n, p)
    return out


def _convolve_truncated(a: np.ndarray, b: np.ndarray, k_max: int) -> np.ndarray:
    """Convolve two PMF vectors, keeping coefficients 0..k_max.

    Uses an FFT convolution for long vectors (O(k log k) rather than
    O(k^2), which is what makes national-scale margins tractable) and
    the direct method for short ones, where the FFT's constant factor
    and floating-point noise are not worth paying. FFT output is
    clipped at zero: the true coefficients are probabilities, so any
    negative value is round-off, not signal.
    """
    if len(a) * len(b) > 250_000:
        from scipy.signal import fftconvolve
        out = fftconvolve(a, b)[: k_max + 1]
        return np.clip(out, 0.0, None)
    return np.convolve(a, b)[: k_max + 1]


@dataclass
class CoalitionResult:
    allocation: Dict[str, float]        # budget share per vector
    attempts: Dict[str, int]
    expected_surviving: Dict[str, float]
    mu_total: float
    m: int
    exact_p_success: float
    chernoff_bound: Optional[float]
    chernoff_tail: str
    p_noticed: float                    # P(at least one attempt flagged, any vector)
    total_cost: float
    utility: float


def coalition_attack(specs: Sequence[VectorSpec], m: int, budget: float,
                     shares: Sequence[float], V: float, D_attack: float,
                     gate_open: Dict[str, bool] | None = None) -> CoalitionResult:
    """G2. Split `budget` across `specs` according to `shares` and
    evaluate the combined attack exactly.

    The exact success probability P(W_total >= m) is computed by
    convolving the component binomial PMFs, because a sum of binomials
    with unequal success probabilities is not binomial. The Chernoff
    bound is computed from the aggregate mean mu_total, which is valid
    because the bound is stated for sums of independent Bernoulli
    variables of arbitrary (possibly unequal) parameters.
    """
    gate_open = gate_open or {}
    shares = np.asarray(shares, dtype=float)
    if shares.sum() <= 0:
        shares = np.ones(len(specs)) / len(specs)
    shares = shares / shares.sum()

    attempts: Dict[str, int] = {}
    expected: Dict[str, float] = {}
    total_cost = 0.0
    p_all_escape = 1.0

    for spec, share in zip(specs, shares):
        open_gate = gate_open.get(spec.name, True)
        n = spec.feasible_attempts(budget * share) if open_gate else 0
        attempts[spec.name] = n
        expected[spec.name] = expected_value(n, spec.p_survive)
        total_cost += n * spec.unit_cost
        p_all_escape *= (1.0 - prob_at_least_one_detected(n, spec.p_detect))

    mu_total = float(sum(expected.values()))
    active = [(spec, attempts[spec.name]) for spec in specs if attempts[spec.name] > 0]

    if not active:
        exact = 1.0 if m <= 0 else 0.0
        return CoalitionResult(
            allocation={s.name: float(w) for s, w in zip(specs, shares)},
            attempts=attempts, expected_surviving=expected, mu_total=0.0, m=m,
            exact_p_success=exact, chernoff_bound=None, chernoff_tail="degenerate",
            p_noticed=0.0, total_cost=0.0,
            utility=exact * V)

    # Exact distribution of the sum, by convolution of component PMFs.
    # Only the failure region is needed: P(W >= m) = 1 - P(W <= m-1), and
    # P(W <= m-1) depends solely on component values <= m-1. Truncating
    # every PMF at m-1 is therefore exact, not an approximation, and it
    # keeps the transform length at m rather than at the total attempt
    # count, which can be two orders of magnitude larger.
    n_total = sum(n for _, n in active)
    if m <= 0:
        exact = 1.0
    elif m > n_total:
        exact = 0.0                     # more votes required than attempts made
    else:
        k_max = m - 1
        dist = np.zeros(k_max + 1)
        dist[0] = 1.0
        for spec, n in active:
            dist = _convolve_truncated(dist,
                                       _binomial_pmf_vector(n, spec.p_survive, k_max),
                                       k_max)
        exact = float(np.clip(1.0 - dist.sum(), 0.0, 1.0))

    cher = chernoff_upper_tail(mu_total, m) if m > mu_total else \
        chernoff_bound_for_threshold(int(sum(n for _, n in active)),
                                     mu_total / max(1, sum(n for _, n in active)), m)

    p_noticed = 1.0 - p_all_escape
    utility = exact * V - total_cost - p_noticed * D_attack

    return CoalitionResult(
        allocation={s.name: float(w) for s, w in zip(specs, shares)},
        attempts=attempts, expected_surviving=expected, mu_total=mu_total, m=m,
        exact_p_success=exact, chernoff_bound=cher.bound, chernoff_tail=cher.tail,
        p_noticed=p_noticed, total_cost=total_cost, utility=utility)


def optimal_coalition(specs: Sequence[VectorSpec], m: int, budget: float,
                      V: float, D_attack: float,
                      gate_open: Dict[str, bool] | None = None,
                      grid_step: float = 0.05) -> Tuple[CoalitionResult, List[CoalitionResult]]:
    """Search the budget simplex for the utility-maximising allocation.

    With three vectors the simplex is two-dimensional, so an exhaustive
    grid at `grid_step` resolution (231 allocations at the 0.05 default)
    is cheap and avoids the local-optimum risk of gradient methods on a
    surface that is piecewise flat wherever floor(B/c) does not change.
    Returns the best allocation and the full evaluated grid, the latter
    being what the allocation-surface figure plots.
    """
    steps = int(round(1.0 / grid_step))
    grid: List[CoalitionResult] = []

    if len(specs) == 3:
        for i in range(steps + 1):
            for j in range(steps + 1 - i):
                k = steps - i - j
                shares = (i / steps, j / steps, k / steps)
                grid.append(coalition_attack(specs, m, budget, shares, V, D_attack, gate_open))
    else:
        for i in range(steps + 1):
            shares = [0.0] * len(specs)
            shares[0] = i / steps
            if len(specs) > 1:
                shares[1] = 1.0 - shares[0]
            grid.append(coalition_attack(specs, m, budget, shares, V, D_attack, gate_open))

    best = max(grid, key=lambda r: r.utility)
    return best, grid
