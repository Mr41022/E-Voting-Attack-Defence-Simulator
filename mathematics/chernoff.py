"""
mathematics/chernoff.py

Chernoff bound implementation for X ~ Binomial(n, p), mu = n*p.

CRITICAL CORRECTNESS REQUIREMENT (per thesis specification section 2.5):

Upper tail (M7):  for threshold m = (1+delta) * mu, delta > 0
    P(X >= (1+delta) mu) <= [e^delta / (1+delta)^(1+delta)]^mu
                          = exp( mu * (delta - (1+delta) ln(1+delta)) )

Lower tail (M8): for threshold m = (1-delta) * mu, 0 < delta < 1
    P(X <= (1-delta) mu) <= exp( -mu * delta^2 / 2 )      <-- NEGATIVE SIGN
    (stronger multiplicative form, also implemented):
    P(X <= (1-delta) mu) <= [exp(-delta) / (1-delta)^(1-delta)]^mu

The lower-tail bound MUST use exp(-mu * delta^2 / 2), never
exp(+mu * delta^2 / 2). The sign is preserved explicitly below and is
unit-tested in tests/test_chernoff.py.

This module does not blindly apply a formula to any (n, p, m). It
first determines whether m sits in the valid upper-tail region
(m > mu), the valid lower-tail region (m < mu), or is degenerate
(m == mu, or mu == 0), and only applies the mathematically applicable
bound. If m does not correspond to a valid delta for either tail, the
function returns None together with a reason string explaining why no
Chernoff bound applies for that specific query -- this is reported
directly to the caller rather than silently substituting a different
formula.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import math


@dataclass
class ChernoffResult:
    bound: Optional[float]
    tail: str            # "upper", "lower", "degenerate", "invalid"
    delta: Optional[float]
    mu: float
    reason: str
    form: Optional[str] = None  # which formula variant was used


def _safe_mu(n: int, p: float) -> float:
    return max(0.0, n) * min(1.0, max(0.0, p))


def chernoff_upper_tail(mu: float, m: float) -> ChernoffResult:
    """M7: bound for P(X >= m) when m > mu (upper tail region).

    delta = m/mu - 1, requires delta > 0.
    """
    if mu <= 0:
        return ChernoffResult(None, "invalid", None, mu,
                               "mu <= 0: distribution is degenerate at 0; "
                               "upper-tail Chernoff bound is not meaningful.")
    if m <= mu:
        return ChernoffResult(None, "invalid", None, mu,
                               "m <= mu: threshold is not above the mean; "
                               "the upper-tail form (delta > 0) does not apply.")

    delta = (m / mu) - 1.0
    if delta <= 0:
        return ChernoffResult(None, "invalid", delta, mu,
                               "Computed delta <= 0; upper-tail bound requires delta > 0.")

    # exponential form: exp( mu * (delta - (1+delta) ln(1+delta)) )
    exponent = mu * (delta - (1 + delta) * math.log1p(delta))
    # exponent is guaranteed <= 0 mathematically; clamp for float noise
    exponent = min(0.0, exponent)
    try:
        bound = math.exp(exponent)
    except OverflowError:
        bound = 0.0
    bound = float(min(1.0, max(0.0, bound)))
    return ChernoffResult(bound, "upper", delta, mu,
                           "Valid upper-tail region (m > mu, delta > 0).",
                           form="exp(mu*(delta-(1+delta)ln(1+delta)))")


def chernoff_lower_tail(mu: float, m: float) -> ChernoffResult:
    """M8: bound for P(X <= m) when m < mu (lower tail region).

    delta = 1 - m/mu, requires 0 < delta < 1.

    IMPORTANT: uses exp(-mu * delta^2 / 2) -- the MINUS sign is
    mathematically required and is never flipped to a plus sign here.
    """
    if mu <= 0:
        return ChernoffResult(None, "invalid", None, mu,
                               "mu <= 0: distribution is degenerate at 0; "
                               "lower-tail Chernoff bound is not meaningful.")
    if m >= mu:
        return ChernoffResult(None, "invalid", None, mu,
                               "m >= mu: threshold is not below the mean; "
                               "the lower-tail form (0 < delta < 1) does not apply.")

    delta = 1.0 - (m / mu)
    if not (0 < delta < 1):
        return ChernoffResult(None, "invalid", delta, mu,
                               "Computed delta is outside (0,1); lower-tail bound "
                               "requires 0 < delta < 1.")

    # Standard additive form -- NEGATIVE SIGN REQUIRED:
    # P(X <= (1-delta)mu) <= exp(-mu * delta^2 / 2)
    exponent_additive = -1.0 * mu * (delta ** 2) / 2.0
    bound_additive = math.exp(exponent_additive)

    # Stronger multiplicative form: [exp(-delta)/(1-delta)^(1-delta)]^mu
    # = exp( mu * ( -delta - (1-delta) ln(1-delta) ) )
    exponent_mult = mu * (-delta - (1 - delta) * math.log1p(-delta))
    exponent_mult = min(0.0, exponent_mult)
    try:
        bound_mult = math.exp(exponent_mult)
    except OverflowError:
        bound_mult = 0.0

    # The multiplicative bound is provably at least as tight; report both
    # but return the tighter (smaller) one as the primary `bound`, and
    # keep the additive one discoverable via `form` string / caller can
    # recompute if needed. We surface the additive value explicitly in
    # the reason for traceability.
    tightest = min(bound_additive, bound_mult)
    tightest = float(min(1.0, max(0.0, tightest)))
    return ChernoffResult(
        tightest, "lower", delta, mu,
        f"Valid lower-tail region (m < mu, 0<delta<1). "
        f"Additive form exp(-mu*delta^2/2) = {bound_additive:.6g}; "
        f"multiplicative form = {bound_mult:.6g}; tighter value returned.",
        form="min(exp(-mu*delta^2/2), multiplicative)"
    )


def chernoff_bound_for_threshold(n: int, p: float, m: float) -> ChernoffResult:
    """Top-level dispatcher: given Binomial(n,p) parameters and a
    manipulation threshold m, determine which (if any) Chernoff tail
    bound is mathematically applicable for approximating P(X >= m),
    and compute it.

    Because the thesis's attack-success condition is X >= m, the
    "attack succeeds" event is naturally an UPPER tail event whenever
    m > mu. We do not apply a lower-tail bound to approximate P(X>=m);
    the lower-tail function above is retained separately for
    completeness / RQ6 exploration (bounding P(X <= m) style events),
    but the dispatcher used by the attack-success experiments always
    resolves to the upper-tail form when applicable.
    """
    mu = _safe_mu(n, p)

    if mu <= 0:
        return ChernoffResult(None, "degenerate", None, mu,
                               "mu = 0 (n=0 or p=0): X is always 0; "
                               "P(X>=m) is trivially 1 if m<=0 else 0, no bound needed.")

    if m <= mu:
        return ChernoffResult(None, "degenerate", None, mu,
                               "Threshold m <= mu: attack success is 'likely' "
                               "under the mean itself; the standard upper-tail "
                               "Chernoff form (delta>0) is not applicable here. "
                               "P(X>=m) should be read from the exact binomial value, "
                               "or from the two-sided certificate in "
                               "chernoff_certificate(), which applies the lower-tail "
                               "(1-delta) form to the failure event.")

    return chernoff_upper_tail(mu, m)


# ---------------------------------------------------------------------
# Two-sided certificate (M7 + M8 applied to the same success event)
# ---------------------------------------------------------------------

@dataclass
class ChernoffCertificate:
    """A Chernoff statement about P(X >= m) that always exists.

    The upper-tail dispatcher above returns a bound only when m > mu.
    That leaves the regime m <= mu -- where the attack is LIKELY to
    succeed, and which is therefore the more alarming half of the
    parameter space -- with no analytic statement at all. This
    certificate closes that gap by bounding whichever tail the
    threshold actually sits in:

        m > mu :  upper tail (M7, the (1+delta) form) bounds
                  P(X >= m) from ABOVE.
        m <= mu:  the failure event X <= m-1 is a LOWER-tail event, so
                  the (1-delta) form (M8) bounds P(X <= m-1) from
                  above, which certifies P(X >= m) from BELOW.

    Both directions are one-sided guarantees, and which one is
    available is a property of the scenario, not a choice. The
    security readings differ accordingly: an upper bound says "the
    attack cannot succeed with probability greater than this", a lower
    bound says "the attack succeeds with probability at least this".

    NOTE ON THE TAIL FORMS. The upper-tail bound uses (1+delta) and the
    lower-tail bound uses (1-delta); these are not interchangeable and
    neither can be substituted for the other. Applying the (1-delta)
    form to an upper-tail event produces a value that is violated by
    the true probability -- see
    tests/test_chernoff.py::test_lower_tail_form_is_invalid_on_upper_tail,
    which demonstrates the violation numerically. The direction of each
    inequality is fixed by which side of the mean the threshold lies on.
    """
    direction: str                      # "upper" | "lower" | "certain" | "impossible"
    tail_bound: Optional[float]         # the bound on the tail actually bounded
    p_success_upper: Optional[float]    # certified upper bound on P(X >= m)
    p_success_lower: Optional[float]    # certified lower bound on P(X >= m)
    delta: Optional[float]
    mu: float
    form: str
    reason: str


def chernoff_certificate(n: int, p: float, m: float) -> ChernoffCertificate:
    """Two-sided Chernoff certificate for the event X >= m.

    Always returns a usable statement: an upper bound on the success
    probability when the threshold is above the mean, and a lower bound
    when it is at or below the mean.
    """
    mu = _safe_mu(n, p)

    if m <= 0:
        return ChernoffCertificate("certain", None, 1.0, 1.0, None, mu,
                                    "trivial",
                                    "Threshold m <= 0 is met by any outcome; "
                                    "P(X >= m) = 1 with no bound required.")
    if n <= 0 or mu <= 0:
        return ChernoffCertificate("impossible", None, 0.0, 0.0, None, mu,
                                    "trivial",
                                    "mu = 0 (n = 0 or p = 0): X is always 0, so "
                                    "P(X >= m) = 0 for m > 0.")
    if m > n:
        return ChernoffCertificate("impossible", None, 0.0, 0.0, None, mu,
                                    "trivial",
                                    "Threshold exceeds the number of trials: "
                                    "P(X >= m) = 0.")

    if m > mu:
        upper = chernoff_upper_tail(mu, m)
        return ChernoffCertificate(
            "upper", upper.bound, upper.bound, 0.0, upper.delta, mu,
            upper.form or "exp(mu*(delta-(1+delta)ln(1+delta)))",
            "Threshold above the mean: the (1+delta) upper-tail form (M7) "
            "bounds the success probability from above.")

    # m <= mu: bound the FAILURE event X <= m-1, a lower-tail event.
    m_fail = m - 1
    if m_fail < 0:
        return ChernoffCertificate("certain", None, 1.0, 1.0, None, mu, "trivial",
                                    "Failure requires X < 0, which is impossible.")
    lower = chernoff_lower_tail(mu, m_fail)
    if lower.bound is None:
        # m-1 == mu exactly: no delta > 0 exists, so no strict statement.
        return ChernoffCertificate(
            "lower", None, 1.0, None, None, mu, "none",
            "Threshold sits exactly at the mean: no admissible delta > 0, so "
            f"no lower-tail bound applies ({lower.reason})")
    p_lower = float(min(1.0, max(0.0, 1.0 - lower.bound)))
    return ChernoffCertificate(
        "lower", lower.bound, 1.0, p_lower, lower.delta, mu,
        lower.form or "min(exp(-mu*delta^2/2), multiplicative)",
        "Threshold at or below the mean: the (1-delta) lower-tail form (M8) "
        "bounds the failure probability P(X <= m-1) from above, which "
        "certifies the success probability from below.")
