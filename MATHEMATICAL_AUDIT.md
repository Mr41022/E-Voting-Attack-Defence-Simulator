# Mathematical Audit

## Verified components

- M1, `Uv = (1-q)R - qP`, matches `mathematics/utility.py::voter_utility`; clamping keeps q in [0,1].
- M2, `R > qP/(1-q)`, is represented by the utility decision and returns no finite threshold at q=1.
- M3, `T = min(N, floor(B/R))`, is implemented in `models/attacker.py`; B <= 0, R <= 0 and N <= 0 produce T=0 by documented convention.
- M4/M9/M12 use binomial distributions and M5/M10/M13 use `scipy.stats.binom.sf(m-1,n,p)`. Edge probes returned the expected values for m <= 0, m > n, p=0, p=1 and n=0.
- M6, `E[X]=np`, is correct.
- M7 uses the negative exponential Chernoff upper-tail exponent and only applies when m > mu.
- M8 uses a negative lower-tail exponent. The certificate correctly applies M8 to the complementary failure event `X <= m-1` when m <= mu.
- M11/M14 use stable detection probabilities and explicitly assume independent acceptance and non-detection, giving surviving probability `q_accept(1-p_detect)`.
- T3 and T7 binary searches rely on monotonicity that holds for fixed n/p or fixed m/p in the stated model.

## Boundary and interpretation concerns

1. The model’s “rational acceptance” is deterministic at scenario level: all T targeted voters accept or all reject because they share q, R and P. It is not a per-voter stochastic acceptance model. This is documented, but headline language should not imply heterogeneous voter behavior.
2. The same symbol q means detection probability in bribery while qs/qb mean acceptance probability for other vectors. This is mathematically documented but easy to misread in figures and prose.
3. Chernoff validation is conditional: 100% containment includes many trivial exact-by-construction rows. The nontrivial upper-tail counts are 1,088 bribery, 3,471 Sybil and 3,604 ballot-stuffing rows.
4. The lower-tail certificate can return no strict bound at m-1 = mu. That is mathematically appropriate, but “every scenario receives a certified statement” is then only true because exact/trivial classifications are included.
5. T4/T5 use utility over T >= 1 while the headline optimiser permits T=0. This is a legitimate definition, but thresholds are not directly the zero crossing of the headline utility.

## Statistical evidence relevant to mathematics

The stored summary reports mean absolute Monte Carlo errors of 0.00008, 0.00039 and 0.00039, but maximum errors of 0.0149, 0.0300 and 0.0230. Relative errors are much larger for low probabilities. The exact calculations are credible; the Monte Carlo agreement does not independently prove the formulas.

## Verdict

The core formulas and numerical edge behavior are consistent with the documented model. No demonstrated arithmetic error was found in the current source. The main mathematical risk is interpretation: abstract probabilities are conditional model outputs, and the two-gate survival construction is an assumption, not an implementation of a real registration/detection process.
