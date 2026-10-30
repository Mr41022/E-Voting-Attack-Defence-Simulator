"""Tests for mathematics/chernoff.py -- especially the negative-sign
requirement on the lower-tail bound."""
import math
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mathematics.chernoff import chernoff_upper_tail, chernoff_lower_tail, chernoff_bound_for_threshold


def test_upper_tail_basic():
    mu = 50.0
    m = 70.0  # delta = 0.4
    res = chernoff_upper_tail(mu, m)
    assert res.tail == "upper"
    assert res.bound is not None
    assert 0 <= res.bound <= 1
    delta = 0.4
    expected = math.exp(mu * (delta - (1 + delta) * math.log1p(delta)))
    assert math.isclose(res.bound, expected, rel_tol=1e-9)


def test_upper_tail_invalid_when_m_below_mu():
    res = chernoff_upper_tail(50.0, 40.0)
    assert res.tail == "invalid"
    assert res.bound is None


def test_lower_tail_negative_sign_required():
    mu = 50.0
    m = 30.0  # delta = 0.4
    res = chernoff_lower_tail(mu, m)
    assert res.tail == "lower"
    delta = 0.4
    additive_correct_sign = math.exp(-mu * delta ** 2 / 2)
    additive_wrong_sign = math.exp(+mu * delta ** 2 / 2)
    # The returned bound must be <= the correctly-signed additive value
    # (it takes the min of additive/multiplicative), and must NOT equal
    # or exceed the wrongly-signed (huge) value.
    assert res.bound <= additive_correct_sign + 1e-9
    assert res.bound < additive_wrong_sign
    assert additive_wrong_sign > 1.0  # sanity: wrong sign blows up past 1


def test_lower_tail_invalid_when_m_above_mu():
    res = chernoff_lower_tail(50.0, 60.0)
    assert res.tail == "invalid"


def test_dispatcher_degenerate_mu_zero():
    res = chernoff_bound_for_threshold(0, 0.5, 5)
    assert res.tail == "degenerate"
    assert res.bound is None


def test_dispatcher_upper_tail_used_for_attack_success():
    res = chernoff_bound_for_threshold(100, 0.3, 50)  # mu=30, m=50 > mu
    assert res.tail == "upper"
    assert res.bound is not None
    assert 0 <= res.bound <= 1


def test_bound_never_negative_or_above_one():
    for mu, m in [(10, 15), (1000, 1500), (5, 5.5), (0.5, 100)]:
        res = chernoff_upper_tail(mu, m) if m > mu else None
        if res and res.bound is not None:
            assert 0.0 <= res.bound <= 1.0


# =====================================================================
# Tail-form correctness: the (1+delta) and (1-delta) forms are not
# interchangeable. These tests exist because the substitution was
# proposed during review, and the refutation belongs in the suite
# rather than in a conversation.
# =====================================================================

def test_lower_tail_form_is_invalid_on_upper_tail():
    """Applying the (1-delta) form to an upper-tail event is violated.

    The claim under test is the (incorrect) statement
        P(X >= (1-d)mu) <= [e^-d / (1-d)^(1-d)]^mu,  d > 0.
    Because (1-d)mu lies BELOW the mean, the event is high-probability
    while the bound decays exponentially, so the inequality fails.
    """
    import math
    from scipy.stats import binom

    violations = 0
    cases = [(200, 0.55), (328, 0.771), (2000, 0.45), (500, 0.4)]
    for n, p in cases:
        mu = n * p
        for d in (0.05, 0.10, 0.20):
            threshold = (1 - d) * mu
            true_prob = binom.sf(math.ceil(threshold) - 1, n, p)
            wrong_bound = math.exp(mu * (-d - (1 - d) * math.log1p(-d)))
            if wrong_bound < true_prob - 1e-12:
                violations += 1
    # The substitution fails on the great majority of these cases; it is
    # not a valid upper-tail bound.
    assert violations >= 10, (
        "expected the (1-delta) form to be violated as an upper-tail bound")


def test_upper_tail_form_holds_where_lower_tail_form_fails():
    """The correctly-signed (1+delta) form bounds every one of the same cases."""
    import math
    from scipy.stats import binom

    for n, p in [(200, 0.55), (328, 0.771), (2000, 0.45), (500, 0.4)]:
        mu = n * p
        for m in (int(mu * 1.05) + 1, int(mu * 1.15) + 1, int(mu * 1.4) + 1):
            if m > n:
                continue
            exact = binom.sf(m - 1, n, p)
            res = chernoff_upper_tail(mu, m)
            assert res.bound is not None
            assert res.bound >= exact - 1e-12


def test_lower_tail_form_holds_on_its_own_tail():
    """Used correctly, the (1-delta) form bounds P(X <= (1-d)mu)."""
    import math
    from scipy.stats import binom

    for n, p in [(200, 0.55), (2000, 0.45), (500, 0.4)]:
        mu = n * p
        for d in (0.05, 0.10, 0.20):
            threshold = (1 - d) * mu
            true_prob = binom.cdf(math.floor(threshold), n, p)
            res = chernoff_lower_tail(mu, threshold)
            assert res.bound is not None
            assert res.bound >= true_prob - 1e-12


# --- two-sided certificate -------------------------------------------

def test_certificate_upper_direction_bounds_success_from_above():
    from mathematics.chernoff import chernoff_certificate
    from scipy.stats import binom
    n, p, m = 500, 0.4, 240          # m > mu = 200
    cert = chernoff_certificate(n, p, m)
    assert cert.direction == "upper"
    exact = binom.sf(m - 1, n, p)
    assert cert.p_success_upper >= exact - 1e-12
    assert cert.p_success_lower == 0.0


def test_certificate_lower_direction_bounds_success_from_below():
    from mathematics.chernoff import chernoff_certificate
    from scipy.stats import binom
    n, p, m = 500, 0.4, 160          # m < mu = 200
    cert = chernoff_certificate(n, p, m)
    assert cert.direction == "lower"
    exact = binom.sf(m - 1, n, p)
    assert cert.p_success_lower <= exact + 1e-12
    assert cert.p_success_upper == 1.0


def test_certificate_always_returns_a_statement():
    """The gap the certificate exists to close: every scenario gets one."""
    from mathematics.chernoff import chernoff_certificate
    for n, p, m in [(500, 0.4, 240), (500, 0.4, 160), (500, 0.4, 200),
                    (0, 0.4, 10), (500, 0.0, 10), (500, 0.4, 900),
                    (500, 0.4, 0), (500, 0.4, 1)]:
        cert = chernoff_certificate(n, p, m)
        assert cert.direction in ("upper", "lower", "certain", "impossible")
        assert cert.reason


def test_certificate_brackets_the_exact_value_across_many_scenarios():
    """Across a sweep, the certified interval always contains the truth."""
    from mathematics.chernoff import chernoff_certificate
    from scipy.stats import binom
    checked = 0
    for n in (50, 200, 1000):
        for p in (0.15, 0.4, 0.75):
            for frac in (0.5, 0.8, 1.0, 1.2, 1.6):
                m = max(1, int(round(n * p * frac)))
                if m > n:
                    continue
                cert = chernoff_certificate(n, p, m)
                exact = binom.sf(m - 1, n, p)
                if cert.p_success_lower is not None:
                    assert cert.p_success_lower <= exact + 1e-9
                if cert.p_success_upper is not None:
                    assert cert.p_success_upper >= exact - 1e-9
                checked += 1
    assert checked > 30
