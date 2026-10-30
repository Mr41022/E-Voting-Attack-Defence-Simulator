# Master Project Audit

## 1. Executive Summary

The project runs at the computational level: compilation passes, the full test suite reports 119 passed, and the existing consistency checker passes. Same-seed in-memory experiments are deterministic and different seeds change scenarios. The clean copied data pipeline reaches experiment, figures, tables and TeX generation, but a complete clean report build is not reproducible without `pdflatex`, and `build_compendium.py` has no no-PDF mode.

The core mathematics is internally consistent with the documented model. The experiments are credible as conditional simulation evidence, not as empirical evidence about deployed elections. The figures are generally scientifically meaningful, with dense threshold/coalition figures needing careful interpretation. The README-level objectives are mostly met, but the concrete security objective is only partially demonstrated.

## 2. Exact Environment

Windows, Python 3.12.10. Dependencies came from `requirements.txt` and were already available. No pytest configuration file was found. `pdflatex` was unavailable, so PDF compilation is NOT VERIFIED in this environment.

## 3. Critical Findings

### HIGH - concrete service authorization and identity bypass

In `evoting_app/service.py`, management methods check only `admin.role`, not service registration/authentication. An unregistered `User` constructed with role `admin` successfully created an election in the audit probe. Re-registering an existing voter ID replaces the stored voter and resets `has_voted`, allowing a second vote under the same identifier. This is a genuine concrete-application security defect. Minimal fix: reject duplicate IDs, require a service-owned authenticated admin/session, and add regression tests.

### HIGH - abstract and concrete experiments estimate different quantities

The abstract layer samples N=200-5,000 and m as a fraction of N; the concrete layer samples N=150-900, support in 0.35-0.65, derives a realized vote-margin threshold, and caps attack attempts differently. Reported baseline/protected rates therefore cannot validate one another. Minimal fix: call the concrete output a qualitative companion, or design a replay/calibration experiment using shared scenarios and estimands.

### HIGH - clean pipeline is not a reproducible build

Existing result files mask dependencies. A clean disposable run with five trials exposed README/report assumptions tied to 2,500 trials and missing generated macros. PDF stages fail without an explicit external LaTeX prerequisite; `build_compendium.py` unconditionally invokes `pdflatex` and does not check its return code. Minimal fix: add one orchestrator, input validation, a no-PDF option to every generator, environment documentation and a clean-build test.

### MEDIUM - bootstrap method is documented inconsistently

`analysis/statistics.py` uses 2,000 bootstrap resamples, while parts of generated methodology/report text state 10,000. This affects reproducibility of interval endpoints. Minimal fix: choose one value and generate the statement from configuration/output.

### MEDIUM - statistical summaries can hide the distribution

Baseline means are 0.350, 0.480 and 0.442 while medians are 0.0, 0.0593 and 0.000017. Means are valid summaries of the sampled scenario distribution, but they are not representative of a typical trial. Report quantiles, distribution plots and paired differences prominently; do not describe mean reductions as universal attack risk.

### MEDIUM - unsupported attribution and economic claims

Identity verification is called the binding weakness without component ablation. Claims that deterrence is cheaper lack a defensive cost model. Minimal fix: remove or scope these claims, or add ablation and explicit cost assumptions.

### MEDIUM - concrete tie handling is unexamined

`election_attack_runner.py` can label a tie-to-candidate transition as a flipped winner. Define tie resolution, exclude ties, or report them separately.

### LOW - service input errors and stale documents

Missing election IDs expose `KeyError` rather than `VotingServiceError`. `results/EXPERIMENTAL_REPORT.md` and `GAME_THEORY_SCENARIOS_REPORT.md` retain obsolete RQ/figure numbering. Generated figure caveats also incorrectly imply every figure uses the `config.py` distribution.

## 4. Mathematical and Security Verdict

M1-M14 and T1-T7 are computationally coherent under explicit assumptions. The blockchain demonstrates hash-linked tamper evidence and mining mechanics. It does not demonstrate distributed consensus, privacy, coercion resistance, secure authentication, Sybil resistance, ballot secrecy or prevention of bribery. Attack acceptance/detection is probability adjustment, not implementation of those controls.

## 5. Assessment

| Dimension | Assessment |
|---|---|
| Problem definition | STRONG |
| Technical difficulty | STRONG |
| Software engineering | ADEQUATE |
| Security understanding | ADEQUATE, with concrete boundary gaps |
| Mathematical correctness | STRONG within model |
| Experimental methodology | ADEQUATE |
| Statistical validity | ADEQUATE, conditional and incompletely reported |
| Reproducibility | WEAK until clean pipeline is fixed |
| Testing quality | STRONG for tested slices, weak at service boundaries |
| Critical evaluation | STRONG in recent correction notes, stale documents remain |
| Originality/extension | STRONG extension scope |
| Scope management | ADEQUATE |
| Results communication | STRONG but dense |
| Academic credibility | ADEQUATE pending claim cleanup |
| Limitations/threats to validity | STRONG in assumptions, unevenly propagated into claims |

Overall: **Potential distinction/A1 quality but weaknesses remain**. The mathematical and experimental framework is MSc-level; the clean-build defect, service authorization flaws, estimand mismatch and unsupported security/economic inferences could prevent a top grade if left unaddressed.

## 6. Twenty Likely Examiner Challenges

1. Why are abstract and concrete rates different estimands?
2. What exactly does the blockchain prevent, and what does it not prevent?
3. Why is a binomial model justified for acceptance and detection?
4. Why are all bribed voters deterministic accept/reject at scenario level?
5. Why is mean success meaningful when the median is nearly zero?
6. Why is 2,000-bootstrap resampling sufficient, and which number is correct?
7. How would component ablation identify the binding countermeasure?
8. How are ties treated in winner-flip rates?
9. How do you reproduce the report from an empty results directory?
10. What changes under adaptive attackers, correlated voters or heterogeneous penalties?
11. Why is `q` detection probability for bribery but `qs` and `qb` acceptance probabilities elsewhere?
12. Why is the Chernoff upper-tail bound omitted when `m <= mu`?
13. Is applying a lower-tail bound to `X <= m-1` a valid certificate for `P(X >= m)`?
14. What does the `attack_success_exact >= 0.5` field mean, and why is it not a statistical test?
15. Does the bootstrap account for the paired design, and what assumptions remain?
16. Why are concrete flip rates reported without intervals, and what would you add?
17. Why does a protected coalition probability of zero not prove impossibility?
18. Are the cost ratios and capacity ceilings measured facts or modelling choices?
19. Why does same-seed reproducibility not imply the PDF/report pipeline is reproducible?
20. What security properties are missing because the blockchain is in-memory and single-process?

Strong answers should explain the relevant formula or code path, state the assumption being relied upon, and avoid promoting a conditional simulation result into a real-world security claim. For questions 1, 5, 6, 7, 8, 9, 15, 16, 17 and 19, the answer should cite the actual numerical or pipeline evidence; for questions 2, 10, 18 and 20, it should clearly separate demonstrated properties from out-of-scope properties.

## 7. Priority Actions

### MUST FIX BEFORE SUBMISSION

1. Fix duplicate-ID and unregistered-admin bypasses and add tests.
2. Make the clean pipeline deterministic from an empty output directory.
3. Resolve the 2,000 versus 10,000 bootstrap inconsistency.
4. Reframe concrete results as a different estimand, not validation.
5. Remove unsupported “cheaper” and component-attribution claims.

### SHOULD FIX

6. Add concrete flip-rate confidence intervals and tie policy.
7. Add quantiles and paired cross-attack uncertainty.
8. Replace stale Markdown result reports and correct figure caveats.
9. Validate CLI inputs and convert raw lookup errors to domain errors.

### NICE TO HAVE

10. Add countermeasure ablations, heterogeneous voters and correlated/adaptive attack sensitivity studies.

## 8. Final Verdict

**RUNNABLE WITH MAJOR ISSUES**.

Technical quality: STRONG conditional framework. Research quality: ADEQUATE to STRONG, but inference boundaries need tightening. Experimental quality: ADEQUATE, with mismatched layers and incomplete uncertainty reporting. Presentation quality: STRONG figures with stale auxiliary documents. MSc thesis readiness: **not submission-ready until the five MUST FIX items are addressed**.
