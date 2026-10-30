# Experimental Report

> **Scope note.** This document reports the core experimental results
> (Figures 1--5, the M1--M14 model). The critical-threshold solvers
> (T1--T7), the unified rational attacker (G1), the coalition attack
> (G2) and Figures 6--10 are covered in the typeset report,
> `report/thesis_report.pdf`, which supersedes this file as the
> complete write-up. Every number in that report is injected at build
> time from `results/json/` and `results/csv/`, so the two cannot
> disagree about any quantity they both discuss.


**Blockchain-Based Electronic Voting System with Mathematical Modelling
and Experimental Evaluation of Bribery, Sybil and Ballot Stuffing
Attacks**

All figures and statistics quoted below are read directly from
`results/json/summary.json` and `results/csv/*.csv`, produced by
`python run_experiments.py --trials 2500 --seed 42` followed by
`python generate_figures.py` and `python generate_tables.py`. No
numbers in this report are invented; re-running with the same seed
reproduces them exactly.

---

## 1. Executive Summary

Across 2,500 paired randomised trials, moving from a **baseline**
e-voting configuration to a **protected**, blockchain-audited
configuration reduced mean attack-success probability by **81.9%**
(bribery), **71.8%** (Sybil), and **73.7%** (ballot stuffing). The
Chernoff upper bound held (i.e. was ≥ the exact probability) in
**100%** of the 1,088–3,604 trials per attack where it was
mathematically applicable, and the Monte Carlo estimator tracked the
exact analytical probability to within a mean absolute error of
0.0001–0.0004 across all three attacks. Under the tested parameter
distribution, **Sybil attacks were the most resilient to
countermeasures** (highest mean protected-configuration success
probability, 13.6%), though all three attacks remained above zero
even under protection — consistent with the report's guiding
principle that countermeasures reduce, but do not eliminate, attack
feasibility.

## 2. Research Objective

To build and experimentally validate a mathematical simulation
framework comparing baseline and blockchain-protected e-voting systems
under bribery, Sybil, and ballot-stuffing attacks, using exact
binomial probability, Monte Carlo simulation, and Chernoff-bound
analysis.

## 3. Research Questions

See §14–21 below, each addressed against RQ1–RQ8 from the project
brief.

## 4. Threat Model

Attacker seeks ≥ `m` successful fraudulent actions out of `N` voters
via bribery, Sybil identities, or ballot stuffing (full detail in
README §3).

## 5–9. Mathematical Model / Bribery / Sybil / Ballot Stuffing / Countermeasures

Full equation traceability is in `MATHEMATICAL_MODEL.md`. Summary
table:

| Attack | Outcome distribution | Success condition |
|---|---|---|
| Bribery | X ~ Binomial(T, 1-q), T=min(N,floor(B/R)) | X >= m |
| Sybil | Y ~ Binomial(S, qs); survives if also undetected | surviving >= m |
| Ballot stuffing | Z ~ Binomial(A, qb); survives if also undetected | surviving >= m |

Countermeasures are modelled purely as probability shifts between
baseline and protected configurations (see `config.py::PARAM_RANGES`
for the exact boost/reduction factors sampled per trial).

## 10. Experimental Methodology

Paired design: one randomised `TrialScenario` generates identical
`(N, m, B, R, P, S, A)` for both baseline and protected runs; only
detection/acceptance probabilities differ (`simulation/scenario_generator.py`).
This isolates the causal effect of the security configuration from
scenario-to-scenario variation.

## 11. Randomisation Method

`numpy.random.default_rng(seed)` throughout; per-trial sub-seeds are
derived deterministically from the top-level seed
(`simulation/experiment_runner.py`), so the full pipeline is
bit-for-bit reproducible for a fixed `--seed` and independent of
Python's global random state.

## 12. Baseline System

Weak detection probability (q, pd, pb sampled from the lower ends of
their configured ranges) and higher fraudulent-action acceptance
probability (qs, qb sampled from the higher ends).

## 13. Protected System

Detection probabilities boosted (`q_protected_boost`,
`pd_protected_boost`, `pb_protected_boost` ranges in `config.py`) and
acceptance probabilities reduced (`qs_protected_reduction`,
`qb_protected_reduction`), representing blockchain-audited signature
verification, identity verification, and ballot validation.

## 14. Bribery Results (RQ1, RQ2, RQ4)

**RQ1 -- attacker resource availability vs success (Figures 1 and 5):**
Mean baseline bribery success probability was **0.350**; mean protected
was **0.064** (absolute reduction 0.287, 95% bootstrap CI
[0.269, 0.304]). The controlled resource sweep shows
`T=min(N,floor(B/R))`
growing linearly in `B` and shrinking in `R` -- the attacker's reach is
a hard ceiling independent of detection probability. The controlled
resource sweep makes this concrete: with a fixed budget `B=60,000` and reward `R=150`
(so `T=floor(B/R)=400`), baseline bribery success is roughly 1.0 for all
tested `N` up to about 3,700 voters (where `m=0.10N <= T`), then collapses
sharply to 0 once `m` exceeds the fixed budget ceiling `T` -- a resource
constraint, not a detection effect.

**RQ2 -- detection probability vs successful manipulation (Figures 1 and
3):** As `q` rises, both the exact and Monte Carlo success
probability fall monotonically (Figure 1), and expected successful
fraudulent votes `E[X]=T(1-q)` fall linearly (Figure 3), as required
by the model.

**RQ4 -- rational voter behaviour (Figure 4):** The voter-utility
heatmap shows the `Uv=0` decision boundary curving through `(R,q)`
space; below/right of the boundary (high reward, low detection risk)
voters rationally accept; above/left they rationally reject.
Critically, the simulation does **not** assume all targeted voters
accept -- `tests/test_briybery.py::test_bribery_scenario_voters_reject_yields_zero_success`
confirms zero fraudulent votes occur whenever `Uv<=0`, regardless of
attacker budget.

**Sample scenario** (trial 1 of the 2,500; full row in
`results/csv/table_10_sample_scenarios_with_threshold.csv`):
`N=2266, m=275, B=122,752, R=257.48, P=1479.12`. At baseline
`q=0.084`, exact `P(X>=m)=1.00`; at protected `q=0.262`, exact
`P(X>=m)=0.00` -- the same underlying electorate and threshold, only the
detection probability changed.

## 15. Sybil Results (RQ1, RQ2)

Mean baseline Sybil success probability (post-detection, "surviving >=
m"): **0.480**; protected: **0.136** (absolute reduction 0.345, 95%
CI [0.327, 0.362], relative reduction 71.8%). Figure 6 shows success
probability rising with attempted identities `S`; Figure 7 shows
expected surviving identities falling as detection probability `pd`
rises. Sybil attacks retained the **highest** mean protected success
probability of the three attack types tested (see §21).

## 16. Ballot Stuffing Results (RQ1, RQ2)

Mean baseline: **0.442**; protected: **0.116** (absolute reduction
0.325, 95% CI [0.308, 0.343], relative reduction 73.7%). Figure 8
(attempts vs success) and Figure 9 (detection probability vs success)
both show the expected monotonic relationships. The controlled
electorate-size sweep shows baseline success falling steeply even without
countermeasures as `N` (and therefore `m`, held at 10% of `N`) grows,
because `A` was fixed as a proportion of `N` in that controlled sweep
-- illustrating that scale alone, independent of security
configuration, affects feasibility once the attempted-fraud count no
longer keeps pace with a rising threshold.

## 17. Chernoff Validation (RQ6)

The Chernoff upper-tail bound was computed wherever `m > mu`
(1,088 valid bribery trials, 3,471 valid Sybil trials, 3,604 valid
ballot-stuffing trials out of 5,000 trial-rows each -- the remainder
had `m <= mu`, where the standard upper-tail form does not apply, per
`mathematics/chernoff.py`). In **100% of valid cases across all three
attacks**, the bound satisfied `Chernoff >= Exact` (mean
conservativeness 0.042 bribery / 0.026 Sybil / 0.022 ballot stuffing;
see Figure 3 and `results/csv/table_06_chernoff_validation.csv`). The
bound is, as expected, conservative rather than tight -- it is never
claimed to approximate the exact probability closely, only to bound
it correctly. The negative-sign correctness of the lower-tail form
(needed for RQ6's discussion of the bound's mathematical structure,
even though the upper-tail form is what is applied to the X>=m success
condition) is separately verified in
`tests/test_chernoff.py::test_lower_tail_negative_sign_required`.

## 18. Monte Carlo Validation (RQ5)

Mean absolute error between the Monte Carlo estimate (2,000 draws per
scenario) and the exact binomial probability was **0.00008**
(bribery), **0.00039** (Sybil), **0.00039** (ballot stuffing) --
i.e. well under half a percentage point on average, confirming the
Monte Carlo engine (`mathematics/binomial.py::sample`, seeded via
`numpy.random.default_rng`) is correctly implemented against the
exact analytical calculation. See Figure 1 for the method comparison and
`results/csv/monte_carlo_convergence.csv` for the convergence
behaviour as sample size grows from 10 to 50,000 draws for a
representative scenario.

## 19. Statistical Analysis

95% confidence intervals (Student's t) are reported for all
baseline/protected means; paired countermeasure-effectiveness
reductions additionally use a 2,000-resample bootstrap (percentile
method) rather than assuming normality, because the underlying
per-trial reduction distribution is bounded in [-1,1] and often
bimodal near 0/1 (visible in the distribution data accompanying Figure 4 -- see
§20). We do not run a battery of significance tests purely for
appearance: the bootstrap CI on the mean paired reduction is the
single test that directly answers "is the countermeasure effect real
and how large is it," which is the quantity of practical interest for
this thesis. Statistical significance (a CI excluding zero, which
holds for all three attacks here) is distinguished explicitly from
practical/security significance: an attack with a statistically
significant but small absolute reduction would still leave a
security-relevant residual risk, which is why absolute (not just
relative) reduction is reported throughout (Figure 4).

## 20. Countermeasure Effectiveness (RQ3, RQ8)

| Attack | Mean baseline | Mean protected | Absolute reduction | Relative reduction |
|---|---|---|---|---|
| Bribery | 0.350 | 0.064 | 0.287 | 81.9% |
| Sybil | 0.480 | 0.136 | 0.345 | 71.8% |
| Ballot stuffing | 0.442 | 0.116 | 0.325 | 73.7% |

(Figure 4 slope chart and its distribution data.) Bribery shows the
**largest relative** reduction --
consistent with its detection probability `q` directly multiplying
into the success probability via `p_success=1-q`, giving
countermeasures a direct lever -- while Sybil shows the **largest
absolute** reduction (0.345) despite the smallest relative one,
because its baseline success probability was also the highest to
begin with.

## 21. Cross-Attack Comparison (RQ7)

Under the tested parameter distribution, **Sybil attacks were the
most resilient**: mean protected-configuration success probability
0.136 vs 0.116 (ballot stuffing) and 0.064 (bribery). This is
reported as a finding **specific to the sampled parameter ranges** in
`config.py` (see §23, Limitations) -- a different choice of
`qs_protected_reduction` / `pd_protected_boost` ranges could change
this ranking, and the report does not claim it generalises beyond the
simulation's assumptions.

## 22. Key Findings

Automatically derived from `results/json/summary.json`
(seed 42, 2,500 trials):

- **Finding 1 (Bribery reduction):** Protected configuration reduced
  mean bribery success probability by 0.287 in absolute terms (81.9%
  relative), 95% bootstrap CI [0.269, 0.304].
- **Finding 2 (Sybil reduction):** 0.345 absolute (71.8% relative),
  95% CI [0.327, 0.362].
- **Finding 3 (Ballot stuffing reduction):** 0.325 absolute (73.7%
  relative), 95% CI [0.308, 0.343].
- **Finding 4 (Monte Carlo error):** Mean |MC - Exact| error was
  under 0.0004 for all three attacks -- the simulation's stochastic engine
  is validated against closed-form probability.
- **Finding 5 (Chernoff validation):** The upper-tail Chernoff bound
  held (bound >= exact) in 100% of the 8,163 mathematically valid
  trial-instances across all three attacks; mean conservativeness was
  0.022-0.042, i.e. the bound typically overstates risk by 2-4
  percentage points versus the exact probability.
- **Finding 6 (Security threshold):** Figure 6 shows that once the
  attacker's approachable population (`T` for bribery, or attempted
  count relative to threshold for Sybil/ballot stuffing) falls below
  the manipulation threshold `m`, success probability collapses
  sharply rather than gradually -- a concrete numerical example is the
  bribery budget ceiling at `T=floor(B/R)`; the controlled sweep is
  available in `results/csv/electorate_size_sweep.csv`.
- **Finding 7 (Most resilient attack):** Sybil attacks, under the
  tested parameter ranges (§21).

*Language used throughout this report follows the brief's guidance:
"under the assumptions of the simulation," "the experimental results
suggest," "the protected configuration reduced" -- no claim is made
beyond what the generated data supports.*

## 23. Threats to Validity

- **Parameter range sensitivity:** all quoted means are averages over
  the specific uniform ranges in `config.py::PARAM_RANGES`; a
  different (e.g. log-uniform, or empirically calibrated) sampling
  distribution could shift the numbers, though the qualitative
  ordering was stable across development seeds.
- **Independence assumptions** (documented fully in `ASSUMPTIONS.md`):
  real fraud attempts, voter decisions, and detection events may be
  correlated in ways this simulation does not capture.
- **Single-shot, non-adaptive attacker:** the simulation does not
  model an attacker who observes partial detection and adapts
  strategy mid-attack.
- **Paired design controls for scenario variation but not for model
  misspecification:** if the underlying binomial/independence
  assumptions do not hold in a real system, the baseline-vs-protected
  comparison would still be internally valid (same misspecification
  applied to both arms) but the absolute numbers would not transfer.

## 24. Limitations

See `ASSUMPTIONS.md` for the complete, categorised list.

## 25. Security Interpretation

Consistent with the brief's explicit requirement: this report never
claims blockchain "completely prevents" or "makes e-voting completely
secure." For bribery specifically, higher detection probability
raises the *risk* to a willing voter but cannot prevent a voter who
values the reward over the detection risk from accepting it -- the
simulation reflects this precisely, since `q` only enters the model
through the risk term in `Uv`, never as a hard block on voter choice.
For Sybil and ballot stuffing, the protected configuration lowers
acceptance probability and raises detection probability, but even the
protected configuration retains a strictly positive mean success
probability across all three attacks in every trial batch produced
during development -- i.e. the model never manufactures a "perfectly
secure" protected outcome, by construction.

## 26. Conclusion

Within the bounds of this synthetic simulation, blockchain-style
audit, signature, identity-verification, and ballot-validation
countermeasures produced large, statistically robust reductions in
modelled attack-success probability across all three attack vectors
(72-82% relative reduction), validated against both exact analytical
probability and an independently-verified Chernoff bound. The
simulation also surfaces a distinct, non-obvious finding -- that
resource ceilings (attacker budget, attempted-fraud count relative to
a growing threshold) can produce sharp rather than gradual collapses
in attack feasibility as electorate size grows -- which is a concrete,
reproducible, and thesis-citable result derived directly from the
implemented mathematical model.
