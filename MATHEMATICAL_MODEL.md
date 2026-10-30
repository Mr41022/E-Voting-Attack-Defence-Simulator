# Mathematical Model — Traceability Document

Every equation below is implemented exactly as specified in the source
material. This document maps each identifier (M1–M14) to its
implementation file/function, states variable definitions, and
records the interpretation applied where the source notes required a
standard-interpretation judgement call (flagged explicitly — see
`ASSUMPTIONS.md` for the full list).

---

### M1 — Rational voter utility
```
Uv = (1-q)R - qP
```
- **Variables:** q = detection probability, R = reward, P = penalty.
- **Implementation:** `mathematics/utility.py::voter_utility`
- **Interpretation:** none required; direct implementation.
- **Limitation:** assumes a risk-neutral voter with linear utility in
  money; does not model loss aversion or non-monetary costs.

### M2 — Incentive-compatibility condition
```
R > qP / (1-q)      (valid for q != 1)
```
- **Implementation:** `mathematics/utility.py::incentive_threshold`
- **Interpretation:** at q = 1 the expression is undefined (division
  by zero). The code returns `None` rather than raising or silently
  substituting a value; the ground-truth decision always falls back
  to the M1 formula, which remains well-defined at q=1 (Uv = -P).

### M3 — Attacker budget constraint
```
T = min(N, floor(B/R))     (R > 0)
```
- **Implementation:** `models/attacker.py::AttackerBudget.max_targets`
- **Interpretation:** B=0, R=0, or B<R all explicitly yield T=0 rather
  than an undefined division. This was not stated as a specific
  numeric convention in the source notes; T=0 (no voters can be
  approached) is the mathematically standard reading and is flagged
  here as an applied interpretation.

### M4 — Bribery outcome distribution
```
X ~ Binomial(T, 1-q)
```
- **Implementation:** `attacks/bribery.py::run_bribery_scenario` via
  `mathematics/binomial.py::sample` / `p_at_least`.

### M5 — Bribery attack-success probability
```
P(X >= m)
```
- **Implementation:** `mathematics/binomial.py::p_at_least`
  (exact, via `scipy.stats.binom.sf(m-1, n, p)`).

### M6 — Expected value
```
mu = T * p
```
- **Implementation:** `mathematics/binomial.py::expected_value`

### M7 — Chernoff upper-tail bound
```
P(X >= (1+delta)mu) <= exp( mu*(delta - (1+delta)ln(1+delta)) ),  delta > 0
```
- **Implementation:** `mathematics/chernoff.py::chernoff_upper_tail`
- Explicitly validated: only applied when `m > mu` (i.e. a genuine
  upper-tail query); otherwise the function returns `tail="invalid"`
  and no bound, rather than silently computing a meaningless number.

### M8 — Chernoff lower-tail bound (NEGATIVE SIGN)
```
P(X <= (1-delta)mu) <= exp( -mu * delta^2 / 2 ),   0 < delta < 1
```
also (stronger, multiplicative form):
```
P(X <= (1-delta)mu) <= [exp(-delta)/(1-delta)^(1-delta)]^mu
```
- **Implementation:** `mathematics/chernoff.py::chernoff_lower_tail`
- **Correctness safeguard:** `tests/test_chernoff.py::test_lower_tail_negative_sign_required`
  explicitly asserts the returned bound is bounded above by the
  correctly-signed `exp(-mu*delta^2/2)` value and is strictly less
  than the (mathematically wrong) `exp(+mu*delta^2/2)` value, which
  would exceed 1 and be nonsensical as a probability bound. The sign
  is hard-coded as `-1.0 * mu * (delta ** 2) / 2.0` and is never
  flipped.
- **Note on usage:** because the thesis's attack-success condition is
  `X >= m` (an upper-tail event), the top-level dispatcher
  `chernoff_bound_for_threshold` used throughout the attack-success
  experiments always resolves to the M7 upper-tail form when
  applicable. `chernoff_lower_tail` is retained as a separate,
  independently-tested function for completeness/RQ6 exploration of
  lower-tail-style events, and is not silently substituted for M7 on
  the event X >= m. It IS applied — correctly — to the complementary
  failure event X <= m-1 by `chernoff_certificate`, which is how the
  two-sided certificate covers the m <= mu regime; see the addendum on
  the coverage gap below.

### M9 — Sybil outcome distribution
```
Y ~ Binomial(S, qs)
```
- **Implementation:** `attacks/sybil.py::run_sybil_scenario`

### M10 — Sybil attack-success probability
```
P(Y >= m)
```
- **Implementation:** `mathematics/binomial.py::p_at_least` (reused).

### M11 — Sybil detection probabilities
```
P(all S escape detection)        = (1-pd)^S
P(at least one detected)          = 1-(1-pd)^S
```
- **Implementation:** `mathematics/probability.py::prob_all_escape_detection`,
  `prob_at_least_one_detected` (log-space, numerically stable for large S).
- **Interpretation:** "surviving" identities (accepted AND not
  detected) are modelled as `W ~ Binomial(S, qs*(1-pd))` under an
  explicit independence assumption between the acceptance gate and
  the detection gate for each attempted identity — see
  `ASSUMPTIONS.md`. The source notes define qs and pd separately but
  do not specify how "surviving" combines them; this is the
  mathematically standard reading under independence and is flagged
  as an applied interpretation.

### M12 — Ballot stuffing outcome distribution
```
Z ~ Binomial(A, qb)
```
- **Implementation:** `attacks/ballot_stuffing.py::run_ballot_stuffing_scenario`

### M13 — Ballot stuffing attack-success probability
```
P(Z >= m)
```
- **Implementation:** `mathematics/binomial.py::p_at_least` (reused).

### M14 — Ballot detection probabilities
```
P(all A escape detection)        = (1-pb)^A
P(at least one detected)          = 1-(1-pb)^A
```
- **Implementation:** `mathematics/probability.py` (same functions as M11,
  applied to the ballot-stuffing parameters).
- **Interpretation:** same independence assumption as M11, applied to
  surviving ballots: `W ~ Binomial(A, qb*(1-pb))`.

---

## Notation reconciliation

Some equivalent presentations of this bribery model label the
per-attempt success probability directly as `q` (i.e.
`X~Binomial(T,q)`, `T=floor(B/c)`). This project's convention
throughout is `q` = **detection** probability, so success probability
is `1-q` (`X~Binomial(T,1-q)`, M4), and `T=min(N,floor(B/R))` (M3)
additionally caps attempts at electorate size `N`. The two
formulations are mathematically identical under the substitution
`q_alt = 1 - q_here` -- nothing in the underlying mathematics changes,
only which symbol carries which meaning. This project's convention was
kept because it composes directly with the rational-voter formula
`Uv=(1-q)R-qP` (M1), where `q` naturally reads as "risk of being
caught." See `results/GAME_THEORY_SCENARIOS_REPORT.md` for the
game-theoretic optimal-attacker extension (M1-M6 composed into an
attacker-level expected-utility search over `T`), which uses this same
`q`=detection convention throughout.

## Summary of applied interpretations (see also ASSUMPTIONS.md)

1. **T=0 convention** for B=0, R=0, or B<R (M3).
2. **Independence between acceptance and detection gates** when
   computing "surviving" fraudulent identities/ballots (M11, M14).
3. **Chernoff dispatcher always resolves to the upper-tail form**
   for attack-success queries (X>=m), since that is the event of
   interest defined in the source notes; the lower-tail form (M8) is
   implemented and tested independently, and is applied by
   `chernoff_certificate` to the complementary FAILURE event X<=m-1
   (a genuine lower-tail event) in order to certify P(X>=m) from below
   when m<=mu. It is never substituted for M7 on the event X>=m.
4. **"Attack success" flag** (`attack_success_exact` fields in the
   CSV output) is defined as `P(...>=m) >= 0.5` purely as a reporting
   convenience threshold for headline success/fail bucketing; the
   underlying continuous probability is always reported alongside it
   and is the quantity actually used in all statistical analysis.

---

# Extension: critical thresholds (T1--T7)

The M-series answers "given these parameters, how likely is the attack
to succeed?". The T-series answers the inverse: "at what parameter
value does the answer change?" Implementation:
`mathematics/thresholds.py`; tests: `tests/test_thresholds.py`.

### T1 --- incentive-compatible reward (identical to M2)
```
R* = qP / (1-q)
```
- **Implementation:** `incentive_reward_threshold`
- Returns no threshold at q=1, where no finite reward is
  incentive-compatible while P>0.

### T2 --- voter-indifference detection probability
```
q_v* = R / (R + P)
```
- **Derivation:** set Uv = 0 in M1: (1-q)R = qP.
- **Implementation:** `voter_indifference_detection`
- **Interpretation:** above q_v* a rational voter refuses any bribe,
  so T collapses to 0 regardless of budget. Depends only on the
  reward-to-penalty ratio -- not on N, m or B.

### T3 --- minimum attempts for a given confidence
```
T_min = min { n : P(X >= m) >= alpha }
```
- **Implementation:** `min_attempts_for_confidence`, exact binary
  search (P(X>=m) is non-decreasing in n for fixed m, p).

### T4 --- attacker break-even budget
```
B* = min { B : max_{T>=1} U(T) > 0 }
```
- **Implementation:** `attacker_break_even_budget`, bisection.
- **Note on the T>=1 restriction:** the headline optimiser includes
  T=0 (declining to attack), so its optimum is never negative and
  cannot be bisected for a zero crossing. The signed utility of
  actually attacking is used instead -- see `best_attacking_utility`
  and ASSUMPTIONS.md.

### T5 --- defender's critical detection probability
```
q_d* = min { q in [0,1] : max_{T>=1} U(T) <= 0 }
```
- **Implementation:** `defender_critical_detection`, bisection on
  [0, q_v*].
- **Guarantee:** q_d* <= q_v* by construction. Below q_d* the attack
  pays; between q_d* and q_v* it is possible but irrational; above
  q_v* it is impossible.

### T6 --- Chernoff-certified safe margin
```
m_eps = min { m : chernoff_upper_bound(n, p, m) <= eps }
```
- **Implementation:** `chernoff_certified_margin`, integer binary
  search (the bound decreases monotonically in m above mu).
- **Interpretation:** a *provable* statement, independent of how many
  Monte Carlo runs were performed. Sufficient for safety, never
  necessary -- it inherits the bound's conservatism.

### T7 --- attacker-reachable margin
```
m_alpha = max { m : P(X >= m) >= alpha }
```
- **Implementation:** `attacker_reachable_margin`.
- **Together with T6:** margins <= m_alpha are comfortably reachable;
  margins >= m_eps are provably out of reach; the band between them is
  where the exact binomial value, not either heuristic, decides.

---

# Extension: unified rational attacker and coalition (G1--G2)

Implementation: `attacks/game_theory.py`; tests:
`tests/test_game_theory.py`.

### G1 --- expected utility of one vector
```
U(n) = P(W >= m) V - n c - [1 - (1-p_detect)^n] D,    W ~ Binomial(n, p_survive)
```
- **Implementation:** `vector_utility` / `optimal_effort`
- The three vectors differ only in (c, p_survive, p_detect, n_ceiling):
  bribery uses (R, 1-q, q, N) plus the M1 rational-voter gate; Sybil
  uses (c_s, qs(1-pd), pd, ceiling); ballot stuffing uses
  (c_b, qb(1-pb), pb, ceiling).
- `optimal_effort` (G1, used for the coalition and per-vector optima)
  searches n on a grid and then refines locally, so the reported n* is
  exact to within one attempt.
- `attacks/bribery_game_theory.py::optimal_attempts` -- the function
  behind Figure 8 and thresholds T4/T5 -- evaluates a 120-point grid
  over [1, T_max] with NO local refinement. Its reported T* is therefore
  accurate to the grid spacing (about 6 attempts at T_max = 666), not to
  a single attempt. The utility curve is flat near its optimum, so this
  does not affect the threshold values, but T* should be read as
  "the best grid point" rather than as an exact argmax.

### G2 --- coalition attack
```
W_total = W_bribery + W_sybil + W_ballot
```
- **Implementation:** `coalition_attack` / `optimal_coalition`
- W_total is a sum of independent binomials with *unequal* success
  probabilities and is therefore not binomial. Its distribution is
  computed EXACTLY by convolving the component PMFs. The convolution
  is truncated at m-1, which is exact rather than approximate:
  P(W>=m) = 1 - P(W<=m-1), and no combination summing to at most m-1
  can involve a component larger than m-1. FFT convolution is used for
  long vectors.
- The Chernoff bound (M7) applies unchanged, since it is stated for
  sums of independent Bernoulli variables with arbitrary and possibly
  unequal parameters; only the aggregate mean mu_total is required.
- **Verified against Monte Carlo:** `test_coalition_exact_matches_monte_carlo`
  compares the convolution result against a 200,000-draw simulation of
  the same three binomials.

---

# Addendum: tail-form correctness and the two-sided certificate

## Which form goes with which tail

The two multiplicative Chernoff bounds are NOT interchangeable:

```
UPPER tail (M7):  P(X >= (1+d) mu) <= [e^d / (1+d)^(1+d)]^mu ,   d > 0
LOWER tail (M8):  P(X <= (1-d) mu) <= [e^-d / (1-d)^(1-d)]^mu ,  0 < d < 1
                                    <= exp(-mu d^2 / 2)
```

The `(1+d)` factor belongs to the upper tail because the threshold sits
ABOVE the mean; the `(1-d)` factor belongs to the lower tail because the
threshold sits BELOW it. Substituting one for the other does not produce
a weaker or stronger bound -- it produces a false statement.

**This was raised in review** ("the upper bound should use `1-delta`"),
so the refutation is recorded here and, more importantly, in the test
suite rather than only in prose:

- `tests/test_chernoff.py::test_lower_tail_form_is_invalid_on_upper_tail`
  evaluates the claim `P(X >= (1-d)mu) <= [e^-d/(1-d)^(1-d)]^mu` for
  d in {0.05, 0.10, 0.20} across four (n,p) settings. The inequality
  fails in 12 of 15 cases, and fails badly: at n=2000, p=0.45, d=0.20
  the true probability is 1.0000 while the claimed bound is 4.0e-9.
  The reason is structural: `(1-d)mu` lies below the mean, so
  `P(X >= (1-d)mu)` is close to 1 while the expression decays
  exponentially in mu.
- `test_upper_tail_form_holds_where_lower_tail_form_fails` confirms the
  correctly-signed `(1+d)` form bounds every one of the same cases.
- `test_lower_tail_form_holds_on_its_own_tail` confirms the `(1-d)` form
  is valid when applied to `P(X <= (1-d)mu)`, which is what it is for.

The upper-tail implementation is therefore unchanged. The sign
conventions in `mathematics/chernoff.py` are correct as written.

## What the review point did expose: a coverage gap (T8)

The dispatcher `chernoff_bound_for_threshold` returns a bound only when
`m > mu`. Every scenario with `m <= mu` -- where the attack is LIKELY to
succeed, and which is therefore the more alarming half of the parameter
space -- received no analytic statement at all. That covered 21%-31% of
trials depending on the vector.

`mathematics/chernoff.py::chernoff_certificate` closes the gap by
bounding whichever tail the threshold actually falls in:

```
m > mu :  upper tail (M7) bounds P(X >= m) from ABOVE
          ->  "the attack succeeds with probability at most B"

m <= mu:  the FAILURE event X <= m-1 is a lower-tail event, so M8 (the
          (1-d) form) bounds P(X <= m-1) from above, which certifies
          P(X >= m) >= 1 - B from BELOW
          ->  "the attack succeeds with probability at least 1-B"
```

Both are one-sided guarantees; which one is available is a property of
the scenario, not a choice. The result is that **every** scenario now
carries a certified statement, and the security reading is arguably
stronger in the lower-tail case: a guaranteed *floor* on attack success
is a more alarming claim than a ceiling.

Implementation: `chernoff_certificate(n, p, m) -> ChernoffCertificate`
with fields `direction`, `tail_bound`, `p_success_lower`,
`p_success_upper`, `delta`, `mu`, `form`, `reason`. The three attack
modules record `chernoff_direction`, `chernoff_success_lower` and
`chernoff_success_upper` per trial.

Validation (`results/json/summary.json::chernoff_certificate_validation`):
across all 15,000 scenario evaluations the certified interval contains
the exact binomial value in 100% of cases, with no scenario left without
a statement. Figure 3 plots both directions against the exact value.


---

# Addendum: discrete support and figure geometry (Figure 7)

Every random variable in this model -- surviving fraudulent votes `X`,
attempts `T`, margins `m` -- is **integer-valued**. That has a
consequence for how the distributions are drawn, which was raised in
review of Figure 7 and is recorded here because it is a property of the
model, not a styling choice.

Plotting a discrete PMF as unit-width centred bars places the bar for
outcome `k` on the interval `[k - 0.5, k + 0.5]`. The event

    {X >= m}

therefore occupies the half-open region whose left edge is at `m - 0.5`,
not at `m`. Drawing the labelled threshold line at `m` puts it through
the *centre* of the first bar of the success region, so the colour
change appears to begin half a vote before the threshold it is labelled
with -- the picture and the label disagree by exactly one half bar
width, even though the shaded mass is exactly correct.

**Convention adopted.** In every figure that draws a discrete
distribution:

| quantity | nature | drawn at |
|---|---|---|
| `m` (manipulation threshold) | boundary between integer outcomes | `m - 0.5` |
| `m_alpha` (T7, reachable) | upper boundary of `{X <= m_alpha}` | `m_alpha + 0.5` |
| `m_eps` (T6, certified) | lower boundary of `{X >= m_eps}` | `m_eps - 0.5` |
| `mu = T(1-q)` | expectation, continuous | `mu` (unmoved) |

Each line is *labelled with the integer margin it separates*, so the
reader still reads `m = 120` while the geometry is honest about where
the region starts.

**Verification.** For the illustrative scenario
`X ~ Binomial(T = 200, 1-q = 0.55)`, `m = 120`:

    P(X >= 120) = binom.sf(119, 200, 0.55) = 0.088073

and the shaded bars sum to `0.088073` to within `1e-12`. The
mathematics was never affected; no probability, threshold, table or
finding in this report changes as a result of the correction. The
geometry is pinned by three tests in `tests/test_figure_geometry.py`
which inspect the Matplotlib rectangle and line coordinates directly.

Annotated standalone source: `figure_07_corrected.py`.
Full correction note: `FIGURE_07_CORRECTION.md`.


---

# Addendum: two success measures for two-gate vectors

Sybil registration and ballot stuffing pass each fraudulent vote
through **two independent gates**; bribery passes it through one. That
produces two different success probabilities for two of the three
vectors, and the distinction must be stated whenever a number is
quoted.

| measure | event | used where |
|---|---|---|
| `P(accepted >= m)` | at least `m` fraudulent votes clear the **acceptance** gate (registration or ballot admission) | intermediate; per-vector tables only |
| `P(surviving >= m)` | at least `m` clear **both** gates: accepted **and** undetected | **headline**; every figure, finding and conclusion |

Formally, with `n` attempts, acceptance probability `q_accept` and
detection probability `p_detect`, the two gates are independent
Bernoulli trials per attempt, so

    accepted   A ~ Binomial(n, q_accept)
    surviving  W ~ Binomial(n, q_accept * (1 - p_detect))

and therefore `P(W >= m) <= P(A >= m)` for every `m`, with equality
only when `p_detect = 0`.

For **bribery** the two coincide by construction: detection is already
folded into the per-attempt success probability `1 - q`, so bribery has
a single effective gate and reports one measure.

## Why both are reported

The gap between the two is itself a result. It separates the part of
the countermeasure effect that comes from tightening **registration and
admission** from the part that comes from **detection** — which is the
practically actionable split for a deployment, since the two are bought
with different mechanisms and at different costs.

At the baseline configuration the two measures differ substantially:

| vector | accepted only | surviving (headline) |
|---|---|---|
| Sybil | 0.5366 | 0.4804 |
| ballot stuffing | 0.4979 | 0.4416 |

## Reporting convention

* Per-vector tables (3, 4) report **both**, with an explicit `measure`
  column and a `measure_definition` column spelling out the event.
* Aggregate tables (5, 7, 8, 9), all figures and all stated findings
  report the **headline** measure only, so that the numbers a reader is
  most likely to quote agree across every table.
* `tests/test_reporting_consistency.py` asserts the agreement, the
  labelling, and the ordering `accepted >= surviving`.

This convention was adopted after review: both numbers had always been
correct, but the per-vector tables reported the acceptance-only figure
under a bare heading `mean`, so a reader comparing them with Tables 7–9
saw an unexplained discrepancy.
