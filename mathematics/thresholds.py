"""
mathematics/thresholds.py

CRITICAL THRESHOLD SOLVERS (thesis extension T1-T7).

The base model (M1-M14) answers "given these parameters, how likely is
the attack to succeed?". This module answers the inverse, and
security-relevant, question: "at what parameter value does the answer
change qualitatively?" Every quantity below is a *threshold* -- a
single number that separates a regime in which the attack is viable
from one in which it is not. These are the numbers annotated directly
onto the figures and quoted in the report, because a defender can act
on a threshold in a way they cannot act on a probability curve.

    T1  R*   incentive-compatible reward     R* = qP/(1-q)          (= M2)
    T2  q_v* voter indifference detection    q_v* = R/(R+P)
    T3  T_min minimum attempts for P(X>=m) >= alpha
    T4  B*   attacker break-even budget      min B s.t. max_T U(T) > 0
    T5  q_d* defender's critical detection   min q s.t. max_T U(T) <= 0
    T6  m_eps Chernoff-certified safe margin min m s.t. bound(m) <= eps
    T7  m_alpha largest margin the attacker beats with prob >= alpha

Sign / existence conventions are explicit throughout: every solver
returns `None` (never a silently substituted default) when the
threshold does not exist inside the searched domain, together with a
machine-readable reason. This mirrors the discipline already applied
in mathematics/chernoff.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import math

from mathematics.binomial import p_at_least, expected_value
from mathematics.chernoff import chernoff_bound_for_threshold
from mathematics.utility import voter_utility


@dataclass
class Threshold:
    """A solved threshold value.

    value  -- the threshold, or None if it does not exist in the domain
    exists -- whether a crossing was found
    label  -- short symbol for figure annotation, e.g. "q_d*"
    reason -- human-readable explanation (always populated)
    """
    value: Optional[float]
    exists: bool
    label: str
    reason: str

    def annotation(self, fmt: str = "{:.4g}") -> str:
        """Text used to annotate this threshold directly on a figure."""
        if not self.exists or self.value is None:
            return f"{self.label} does not exist"
        return f"{self.label} = {fmt.format(self.value)}"


# ---------------------------------------------------------------------
# T1 / T2 -- voter-side thresholds (closed form)
# ---------------------------------------------------------------------

def incentive_reward_threshold(q: float, P: float) -> Threshold:
    """T1 (= M2). Smallest bribe R above which a rational voter accepts.

        Uv = (1-q)R - qP > 0   <=>   R > qP/(1-q)

    Undefined at q = 1 (certain detection): no finite reward makes
    acceptance rational when P > 0, so no threshold exists.
    """
    q = min(1.0, max(0.0, q))
    if math.isclose(q, 1.0):
        return Threshold(None, False, "R*",
                         "q = 1 (certain detection): Uv = -P, so no finite reward "
                         "is incentive-compatible while P > 0.")
    return Threshold((q * P) / (1 - q), True, "R*",
                     "Rational voters accept any bribe strictly above this reward.")


def voter_indifference_detection(R: float, P: float) -> Threshold:
    """T2. Detection probability at which the targeted voter is exactly
    indifferent between accepting and refusing the bribe.

        (1-q)R = qP   <=>   q_v* = R / (R + P)

    Above q_v* the bribe is rejected outright, so the attack collapses
    to T = 0 regardless of the attacker's budget. This is the single
    most actionable defender-side number in the bribery model: it
    depends only on the ratio of reward to penalty, not on N, m or B.
    """
    if R <= 0 and P <= 0:
        return Threshold(None, False, "q_v*",
                         "R = P = 0: the voter is indifferent everywhere; "
                         "no isolated threshold exists.")
    if (R + P) <= 0:
        return Threshold(None, False, "q_v*", "R + P <= 0: threshold undefined.")
    return Threshold(R / (R + P), True, "q_v*",
                     "Detection probability at which voter utility Uv = 0; "
                     "above it a rational voter always refuses.")


# ---------------------------------------------------------------------
# T3 -- effort threshold (monotone integer search)
# ---------------------------------------------------------------------

def min_attempts_for_confidence(p_success: float, m: int, alpha: float = 0.5,
                                 n_max: int = 10_000_000) -> Threshold:
    """T3. Smallest number of attempts n such that P(X >= m) >= alpha,
    for X ~ Binomial(n, p_success).

    P(X >= m) is non-decreasing in n for fixed m and p, so a binary
    search over n is exact. Returns None when even n_max attempts
    cannot reach the requested confidence (e.g. p_success = 0).
    """
    if m <= 0:
        return Threshold(0.0, True, "T_min",
                         "Threshold m <= 0 is satisfied by zero attempts.")
    p_success = min(1.0, max(0.0, p_success))
    if p_success <= 0:
        return Threshold(None, False, "T_min",
                         "p_success = 0: no number of attempts yields a success.")
    if p_at_least(n_max, p_success, m) < alpha:
        return Threshold(None, False, "T_min",
                         f"Even n = {n_max:,} attempts do not reach "
                         f"P(X >= m) >= {alpha}.")

    lo, hi = m, n_max            # n < m is impossible, so start at m
    while lo < hi:
        mid = (lo + hi) // 2
        if p_at_least(mid, p_success, m) >= alpha:
            hi = mid
        else:
            lo = mid + 1
    return Threshold(float(lo), True, "T_min",
                     f"Fewest attempts reaching P(X >= m) >= {alpha}.")


# ---------------------------------------------------------------------
# Shared helper: monotone bisection on a real parameter
# ---------------------------------------------------------------------

def _bisect_crossing(f: Callable[[float], float], lo: float, hi: float,
                     tol: float = 1e-6, max_iter: int = 200) -> Optional[float]:
    """Find x in [lo, hi] where f changes sign, assuming f(lo) and f(hi)
    bracket a crossing. Returns None if they do not.
    """
    f_lo, f_hi = f(lo), f(hi)
    if f_lo == 0:
        return lo
    if f_hi == 0:
        return hi
    if (f_lo > 0) == (f_hi > 0):
        return None
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        f_mid = f(mid)
        if abs(hi - lo) < tol:
            return mid
        if (f_mid > 0) == (f_lo > 0):
            lo, f_lo = mid, f_mid
        else:
            hi, f_hi = mid, f_mid
    return 0.5 * (lo + hi)


# ---------------------------------------------------------------------
# T4 / T5 -- attacker/defender economic thresholds
# ---------------------------------------------------------------------

def best_attacking_utility(N: int, m: int, B: float, R: float, P: float, q: float,
                            V: float, D_attack: float) -> float:
    """Best expected utility achievable by an attacker who actually
    mounts an attack, i.e. max over T >= 1 rather than over T >= 0.

    This distinction matters for every threshold below. The headline
    optimiser in attacks/bribery_game_theory.py includes T = 0 in its
    search, because a rational attacker can always walk away; its
    reported optimum is therefore never negative, and a quantity that
    is floored at zero cannot be bisected for a zero crossing. The
    thresholds here need the *signed* payoff of attacking, which is
    negative precisely when attacking is a losing proposition. Where
    not even one attempt is affordable, a sentinel of -(V + D + R) is
    returned: strictly negative, so the search treats "cannot attack"
    and "should not attack" alike, and finite, so bisection stays
    well behaved.
    """
    from attacks.bribery_game_theory import optimal_attempts  # local: avoids cycle

    res = optimal_attempts(N, m, B, R, P, q, V, D_attack)
    attacking = [pt.utility for pt in res.curve if pt.T >= 1]
    if not attacking:
        return -(abs(V) + abs(D_attack) + abs(R))
    return max(attacking)


def attacker_break_even_budget(N: int, m: int, R: float, P: float, q: float,
                                V: float, D_attack: float,
                                B_max: Optional[float] = None,
                                tol: float = 1e-3) -> Threshold:
    """T4. Smallest budget B at which mounting the attack first becomes
    profitable in expectation.

        B* = min { B : max_{1 <= T <= min(N, floor(B/R))} U(T) > 0 }

    Because the feasible set {T : T <= min(N, floor(B/R))} grows with
    B, the maximum is non-decreasing in B, so the crossing is unique
    where it exists. Below B* the attack is not worth mounting even
    when it is technically possible -- the defender does not have to
    make the attack impossible, only unprofitable.
    """
    if R <= 0 or N <= 0:
        return Threshold(None, False, "B*",
                         "R <= 0 or N <= 0: no feasible bribery programme exists.")
    if voter_utility(q, R, P) <= 0:
        return Threshold(None, False, "B*",
                         "Bribe is not incentive-compatible at this q: voters refuse "
                         "at any budget, so utility never turns positive.")

    B_ceiling = B_max if B_max is not None else float(N * R)

    def utility_of_attacking(B: float) -> float:
        return best_attacking_utility(N, m, B, R, P, q, V, D_attack)

    if utility_of_attacking(B_ceiling) <= 0:
        return Threshold(None, False, "B*",
                         f"Even a saturating budget B = {B_ceiling:,.0f} (enough to "
                         f"approach every voter) leaves expected utility <= 0.")
    if utility_of_attacking(R) > 0:
        return Threshold(float(R), True, "B*",
                         "A single bribe already yields positive expected utility.")

    crossing = _bisect_crossing(utility_of_attacking, R, B_ceiling, tol=tol)
    if crossing is None:
        return Threshold(None, False, "B*", "No sign change bracketed in [R, B_max].")
    return Threshold(float(crossing), True, "B*",
                     "Smallest budget at which the attack becomes profitable in "
                     "expectation.")


def defender_critical_detection(N: int, m: int, B: float, R: float, P: float,
                                 V: float, D_attack: float,
                                 tol: float = 1e-6) -> Threshold:
    """T5. Smallest detection probability q at which mounting the attack
    stops paying -- the defender's design target.

        q_d* = min { q in [0,1] : max_{T >= 1} U(T) <= 0 }

    Two mechanisms drive utility downward as q rises, and the solver
    captures both. The survival probability of a bribed vote, 1-q,
    falls, so P(flip) falls and the expected detection penalty rises;
    and beyond the voter-indifference point q_v* = R/(R+P) the bribe
    stops being accepted at all, so the attack cannot proceed on any
    budget. The returned value is therefore never above q_v*, and the
    report reads q_d* as "how good detection must be before this
    attack stops paying".
    """
    q_v = voter_indifference_detection(R, P)
    hi = q_v.value if q_v.exists and q_v.value is not None else 1.0
    hi = min(1.0, max(0.0, hi))
    # Stay strictly inside the incentive-compatible region: at exactly
    # q_v* the voter is indifferent, refuses under the strict Uv > 0
    # rule, and the utility of attacking is identically zero.
    hi_eff = max(0.0, hi - 1e-9)

    def utility_of_attacking(q: float) -> float:
        return best_attacking_utility(N, m, B, R, P, q, V, D_attack)

    if utility_of_attacking(0.0) <= 0:
        return Threshold(0.0, True, "q_d*",
                         "The attack is already unprofitable with no detection at "
                         "all; detection is not the binding constraint here.")

    if utility_of_attacking(hi_eff) > 0:
        return Threshold(float(hi), True, "q_d*",
                         "Expected utility stays positive right up to the voter-"
                         "indifference bound: the attack is stopped by voter "
                         "refusal (q_v*) rather than by detection itself.")

    crossing = _bisect_crossing(utility_of_attacking, 0.0, hi_eff, tol=tol)
    if crossing is None:
        return Threshold(float(hi), True, "q_d*",
                         "Utility reaches zero only at the voter-indifference "
                         "bound, where bribes stop being accepted.")
    return Threshold(float(crossing), True, "q_d*",
                     "Detection probability above which the attack no longer pays "
                     "in expectation.")


# ---------------------------------------------------------------------
# T6 / T7 -- margin thresholds (what majority is provably safe?)
# ---------------------------------------------------------------------

def chernoff_certified_margin(n: int, p: float, epsilon: float = 1e-3) -> Threshold:
    """T6. Smallest margin m for which the Chernoff upper bound certifies
    P(X >= m) <= epsilon.

    This is a *provable* statement rather than an empirical one: it does
    not depend on how many Monte Carlo runs were performed. A defender
    can quote it as "a lead of m votes cannot be overturned by this
    attacker except with probability at most epsilon".

    The bound is monotonically decreasing in m above mu, so integer
    binary search over m in (mu, n] is exact.
    """
    n = int(max(0, n))
    p = min(1.0, max(0.0, p))
    mu = expected_value(n, p)

    if n == 0 or p <= 0:
        return Threshold(1.0, True, "m_eps",
                         "mu = 0: a single vote of margin is already unreachable.")
    if chernoff_bound_for_threshold(n, p, n).bound is None:
        return Threshold(None, False, "m_eps",
                         "No valid Chernoff region: mu >= n, bound not applicable.")
    if (chernoff_bound_for_threshold(n, p, n).bound or 1.0) > epsilon:
        return Threshold(None, False, "m_eps",
                         f"Even m = n = {n:,} is not certified at epsilon = {epsilon:g}.")

    lo, hi = int(math.floor(mu)) + 1, n
    while lo < hi:
        mid = (lo + hi) // 2
        res = chernoff_bound_for_threshold(n, p, mid)
        b = res.bound if res.bound is not None else 1.0
        if b <= epsilon:
            hi = mid
        else:
            lo = mid + 1
    return Threshold(float(lo), True, "m_eps",
                     f"Chernoff-certified safe margin at epsilon = {epsilon:g}.")


def attacker_reachable_margin(n: int, p: float, alpha: float = 0.5) -> Threshold:
    """T7. Largest margin m the attacker overturns with probability at
    least alpha, i.e. max { m : P(X >= m) >= alpha }.

    Together with T6 this brackets the contested region: margins at or
    below m_alpha are comfortably within reach; margins at or above
    m_eps are provably out of reach; everything in between is where
    the exact binomial calculation actually matters.
    """
    n = int(max(0, n))
    p = min(1.0, max(0.0, p))
    if n == 0 or p <= 0:
        return Threshold(0.0, True, "m_alpha",
                         "mu = 0: the attacker cannot overturn any positive margin.")
    if p_at_least(n, p, 1) < alpha:
        return Threshold(0.0, True, "m_alpha",
                         f"Even a single fraudulent vote arrives with probability "
                         f"below {alpha}.")

    lo, hi = 1, n
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if p_at_least(n, p, mid) >= alpha:
            lo = mid
        else:
            hi = mid - 1
    return Threshold(float(lo), True, "m_alpha",
                     f"Largest margin overturned with probability >= {alpha}.")
