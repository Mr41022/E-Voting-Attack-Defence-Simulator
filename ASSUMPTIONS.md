# Assumptions and Limitations

This document explicitly records every modelling assumption made by
the simulation, and the limitations that follow from them. Nothing
here is hidden inside the code; every assumption listed is also
referenced from the corresponding module's docstring.

## Core simulation assumptions

- **Synthetic data only.** No real voters, identities, elections, or
  organisations are modelled or referenced. All identifiers (`vote_id`,
  `synthetic_voter_id`, etc.) are simulation-internal strings/indices.
- **Independent Bernoulli trials.** Each targeted voter's bribery
  outcome, each attempted Sybil identity's acceptance/detection, and
  each attempted fraudulent ballot's acceptance/detection are modelled
  as independent Bernoulli trials with a constant probability within a
  given scenario. Real-world correlation (e.g. a single compromised
  registration official affecting many identities at once) is out of
  scope.
- **Constant probability within a scenario.** q, qs, pd, qb, pb are
  held fixed for the duration of a single trial's evaluation. They are
  not modelled as time-varying or adaptive within a trial.
- **Rational voter assumption.** Bribed voters accept an offer if and
  only if Uv > 0 under the M1 formula. Real voters may not behave
  perfectly rationally (bounded rationality, ideology, risk aversion,
  social pressure); this is a simplifying assumption, not an empirical
  claim about real electorates.
- **Homogeneous targeted-voter population per scenario.** Because all
  T targeted voters in a bribery scenario face identical (q,R,P), the
  base model does not introduce per-voter heterogeneity in utility
  parameters. This is a scope decision: modelling a distribution of
  voter-specific penalties/rewards would require additional
  unspecified parameters not present in the source notes.
- **Attacker resource constraints are hard limits.** The attacker
  cannot exceed the budget B (bribery) or the attempted counts S/A
  (Sybil/ballot stuffing) supplied for a given trial.
- **Abstraction of "attack attempts."** S and A represent the number
  of attempted fake identities / fraudulent ballots as an abstract
  count; the simulation does not model the operational mechanics of
  how those attempts are technically executed.
- **Detection probabilities are simulation parameters, not
  guarantees.** q, pd, pb represent the probability an item is
  detected under a given system configuration. They are supplied
  (baseline) or derived via a configurable boost factor (protected);
  see `config.py`. No claim is made that these numbers reflect any
  specific real deployed system.
- **Blockchain abstraction.** The "blockchain" in this project
  (`countermeasures/blockchain.py`) is an in-memory, append-only
  record store used to illustrate an audit-trail pipeline. It is NOT
  a peer-to-peer distributed ledger, does not implement consensus, and
  is not a cryptocurrency. SHA-256 (via Python's standard `hashlib`)
  is used only to produce realistic-looking transaction/signature hash
  strings for audit-record realism — no cryptographic security
  property is claimed or relied upon.
- **Countermeasure abstraction.** "Digital signatures," "identity
  verification," "duplicate detection," and "ballot validation" are
  modelled purely as probability adjustments (lower acceptance
  probability, higher detection probability) between the baseline and
  protected configurations. The simulation does not implement or claim
  to implement production-grade cryptographic identity or signature
  systems.
- **Independence between the "acceptance" and "detection" gates**
  when computing surviving fraudulent Sybil identities / ballots
  (see MATHEMATICAL_MODEL.md, M11/M14 interpretation note).

## Explicit interpretations of ambiguous source material

Per the master prompt's directive ("if something in the source
material is ambiguous: identify the ambiguity; do not silently change
it; implement the mathematically standard interpretation only if
justified; document the interpretation"), the following judgement
calls were made and are documented here (and cross-referenced in
MATHEMATICAL_MODEL.md):

1. T=0 convention when B=0, R=0, or B<R (source notes say "handle
   carefully" without specifying the exact numeric convention).
2. Independence assumption combining qs/pd and qb/pb into a "surviving"
   binomial parameter (source notes define the two probabilities
   separately but do not give an explicit combination formula for
   "surviving" counts).
3. Two Chernoff entry points, with different scopes.
   - `chernoff_bound_for_threshold`, the ONE-SIDED dispatcher used for
     the attack-success bound columns, always resolves to the
     upper-tail (M7) form and returns nothing when m <= mu.
   - `chernoff_certificate`, the TWO-SIDED certificate added after
     review, does apply the lower-tail form (M8) when m <= mu — not to
     the event X>=m directly, but to the complementary failure event
     X<=m-1, which IS a lower-tail event. Bounding that from above
     certifies P(X>=m) from BELOW. This is a valid use of M8, not a
     substitution of M8 for M7, and it is what fills the
     `chernoff_success_lower` column and the right-hand panel of
     Figure 3. An earlier version of this file said M8 "is not applied
     to the X>=m success condition", which was true before the
     certificate existed and is now misleading.
4. The `attack_success_exact` boolean field is a >=0.5 probability
   threshold used only as a convenience label in exported CSVs; it is
   never used as the basis for any statistical test or headline number
   in the report — the underlying continuous probability is used
   throughout.

## Limitations (threats to validity)

- Real voter behaviour may be correlated across voters (e.g. social
  network effects, coordinated bribery campaigns), which the
  independent-Bernoulli-trial assumption does not capture.
- Detection probabilities in a real system would likely vary over
  time and be adaptively updated by defenders; this simulation treats
  them as fixed per scenario.
- A real attacker may adapt strategy dynamically in response to
  partial success/failure; this simulation evaluates single static
  scenarios rather than a repeated/adaptive game.
- Real security mechanisms interact in complex, non-independent ways
  (e.g. a compromised signature scheme could simultaneously defeat
  duplicate detection); the simulation models each countermeasure's
  effect only through the aggregate acceptance/detection probability
  parameters.
- Voters may not behave perfectly rationally in practice; utility
  maximisation is a modelling idealisation.
- Real election systems have substantially more operational complexity
  (voter registration workflows, physical security, multi-party
  oversight, legal remedies) that this simulation does not attempt to
  represent.
- Blockchain-based recording does not inherently eliminate bribery: a
  voter who is willing to sell their vote can still do so regardless
  of how immutably the resulting vote is recorded; the simulation
  reflects this by modelling blockchain-style countermeasures as
  raising *detection* probability, not as directly preventing a
  willing voter's decision to accept a bribe (see M1/M2, unaffected by
  q's value except through the detection-risk term).
- Sybil resistance in the simulation depends entirely on the supplied
  qs/pd parameters; it does not model the specific technical mechanism
  (e.g. biometric verification, KYC, proof-of-personhood) that would
  produce those probabilities in a real deployment.
- Ballot-stuffing resistance likewise depends entirely on the supplied
  qb/pb parameters, not a specific validation-technology model.

## Assumptions introduced by the threshold extension (T1--T7)

- **Threshold non-existence is reported, never defaulted.** Every
  solver in `mathematics/thresholds.py` returns `Threshold(value=None,
  exists=False, reason=...)` when the crossing it looks for does not
  occur inside the searched domain. No solver substitutes an endpoint,
  a zero, or a "large number" for a threshold that does not exist. The
  reason string is carried through to the CSV and JSON output. The
  figures do NOT print "does not exist": `mark_vline`/`mark_hline`
  return without drawing when the value is absent or non-finite, so a
  non-existent threshold is simply absent from the plot, and the
  figure's caption or surrounding prose is where its absence is
  explained. (Stated precisely here after review found the earlier
  wording claimed an on-figure annotation that no figure emits.)
- **Break-even and critical-detection thresholds are defined on the
  utility of *attacking*, not on the headline optimiser.** The
  headline optimum `max_{T>=0} U(T)` is never negative, because a
  rational attacker may always decline; a quantity floored at zero
  cannot be solved for a zero crossing. T4 and T5 therefore use
  `max_{T>=1} U(T)`, which is negative exactly when attacking is a
  losing proposition. Where not even one attempt is affordable, a
  finite negative sentinel is returned so that bisection stays well
  defined. This is a definitional choice, not a mathematical necessity,
  and is stated wherever those thresholds are quoted.
- **Monotonicity is assumed for the bisection solvers.** T4 relies on
  `max_{T>=1} U(T)` being non-decreasing in B (the feasible set grows
  with budget) and T5 on it being non-increasing in q (survival falls
  and expected penalty rises together). Both hold for the model as
  specified; a model in which detection also reduced the penalty, say,
  would break the assumption and the solver with it.
- **The Chernoff-certified margin inherits the bound's
  conservatism.** T6 reports the smallest margin the *bound* certifies
  at tolerance epsilon, which is always at least as large as the
  smallest margin that is genuinely safe at epsilon. It is a sufficient
  condition for safety, never a necessary one, and the gap between it
  and the attacker-reachable margin (T7) is reported explicitly as the
  "contested band" rather than being papered over.

## Assumptions introduced by the coalition extension (G1--G2)

- **Vectors are mutually independent.** The three vectors are assumed
  not to interfere: forging identities neither helps nor hinders
  bribery, and detecting one vector does not raise suspicion about the
  others. This is a strong assumption and almost certainly optimistic
  for the defender in one respect (a real audit triggered by one
  anomaly would examine everything) and pessimistic in another (an
  attacker with insider access likely gains on several vectors at
  once). It is what makes the exact convolution in
  `attacks/game_theory.py` valid; correlated vectors would require a
  joint model.
- **Relative costs are assumed, not measured.** A forged identity is
  assumed to cost 40% of a bribe and an injected ballot 15%. No public
  data grounds these ratios. They are declared as named constants in
  `simulation/threshold_analysis.py`, and the sensitivity sweep in
  `run_threshold_analysis.py` re-runs the analysis across 108
  combinations of both ratios and both capacity ceilings so that no
  reported conclusion rests on the specific values chosen.
- **Capacity ceilings are structural, not budgetary.** Bribery is
  capped at N by M3. Forged registrations are capped at 20% of N and
  injected ballots at 30% of N, representing what the surrounding
  process would absorb without a self-evident anomaly (a registration
  window of bounded size; a turnout figure that must stay plausible).
  These ceilings are modelling choices standing in for detection
  mechanisms not otherwise represented, and they materially affect the
  coalition result: without them the cheapest vector saturates and the
  allocation question becomes trivial. They too are swept in the
  sensitivity analysis.
- **Budget shares are searched on a discrete grid.** The optimal
  allocation is found by exhaustive evaluation of the budget simplex at
  a 0.05 step (231 allocations for three vectors), not by continuous
  optimisation. The utility surface is piecewise flat wherever
  floor(B/c) does not change, so a gradient method would be unreliable;
  the reported optimum is the best grid point, which may differ
  slightly from the true continuous optimum.
- **The coalition success probability is exact, not approximate.** The
  sum of binomials with unequal success probabilities is computed by
  convolution of the component PMFs, truncated at m-1. The truncation
  is exact rather than approximate, because no combination summing to
  at most m-1 can involve a component larger than m-1. No normal,
  Poisson, or Poisson-binomial approximation is used anywhere.
