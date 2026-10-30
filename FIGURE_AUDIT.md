# Figure Audit

All ten PNG/PDF figure assets were present. Captions and underlying source paths were inspected; representative PNGs were visually inspected for labels, scales, legends and annotations.

| Figure | Question/data | Strengths | Weaknesses and recommendation | Status |
|---|---|---|---|---|
| 1 method comparison | Exact vs Monte Carlo vs Chernoff over q; fixed scenario | Clear method comparison, probability axis and incentive boundary | Dense title and annotations; Monte Carlo sample size is large but one scenario only | Keep, main text |
| 2 voter utility | M1 surface and T2 boundary | Formula and solver boundary are visible and labelled | A surface is not evidence of real voter behavior; explicitly model-derived | Keep, with caveat |
| 3 Chernoff certificate | Exact probability vs certified bounds | Correctly separates upper/lower directions and reports counts | Dense scatter and many trivial exact cases can look stronger than nontrivial validation | Keep, possibly appendix if space is tight |
| 4 attack comparison | Abstract baseline/protected means | Zero-anchored comparison and labelled residuals | Mean-only comparison hides medians near zero and heterogeneous scenarios | Keep with distribution/CI companion |
| 5 concrete flip rate | Mined-election winner flips | Directly shows concrete outcome metric and zero-based scale | Different estimand/ranges from abstract layer; no concrete CIs | Keep, but call it a separate experiment, not validation |
| 6 critical detection | Bribery utility against q | Thresholds and protected operating point are readable | Utility scale is dominated by large values; economic conclusions lack a cost model | Keep, but move cost claims to limitations |
| 7 binomial thresholds | PMF, mean, m_alpha and m_eps | Strong mathematical communication; half-integer boundary is explained | m_alpha and mean are close and annotation overlap remains possible | Keep, main text |
| 8 optimal attacker | Utility and flip probability vs T | Shows non-budget-exhausting optimum and grid qualification | Fixed scenario and grid point; utility magnitudes are not externally calibrated | Keep, with grid limitation |
| 9 vector capacity | Expected capacity, exact full-effort P, coalition marker | Correctly distinguishes expectation from probability; avoids prior budget-infeasible sum | Log scale and multiple annotations require careful reading | Keep, strong figure |
| 10 coalition | Coalition vs best pure attack | Shows benchmark-specific coalition effect and protected residual | Protected zeros can visually imply impossibility; only five fixed scenarios | Keep in main text or compact extension section |

## Top five strongest

1. Figure 1: direct exact/Monte Carlo/bound comparison.
2. Figure 3: explicit Chernoff direction and containment distinction.
3. Figure 5: concrete winner-flip estimand.
4. Figure 7: threshold mathematics and integer support.
5. Figure 9: corrected distinction between expected capacity and success probability.

## Appendix candidates

Figures 3, 8, 9 and 10 are technically valuable but dense. If the thesis argument must be shortened, keep Figures 1, 5 and 7 in the main body and move the others to an appendix with explicit cross-references.
