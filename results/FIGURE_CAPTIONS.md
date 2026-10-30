# Figure Captions

The dissertation uses ten figures, numbered here in order of appearance in the report. Every numeric claim below is computed from the same data the figure plots, so a caption cannot drift away from its figure.

## Figure 1 --- Method comparison

- **File:** `fig_01_method_comparison.png` / `fig_01_method_comparison.pdf`
- **Purpose:** Exact binomial, Monte Carlo and Chernoff bound as detection probability varies, on a single fixed scenario so that all three methods are computed for the same parameters.
- **Variables:** x = q (detection probability); y = P(X>=m)
- **Observation:** The Monte Carlo estimate is indistinguishable from the exact binomial curve at this sample size, while the Chernoff bound lies strictly above both wherever it is defined -- valid, but visibly conservative. Success stays near certainty and then collapses over a narrow band of q, which is why detection is the efficient defensive lever.
- **Statistical caveat:** values characterise behaviour under the parameter distribution declared in `config.py`, not a universal guarantee.

## Figure 2 --- Voter utility threshold

- **File:** `fig_02_voter_utility_threshold.png` / `fig_02_voter_utility_threshold.pdf`
- **Purpose:** Rational voter utility surface with the decision boundary and the closed-form indifference threshold q_v* = R/(R+P) traced on top of it.
- **Variables:** x = R (bribe reward); y = q (detection probability)
- **Observation:** The numerically computed zero contour of M1 and the closed-form threshold T2 coincide exactly, confirming that the solver and the formula describe the same boundary. Above the threshold a rational voter refuses any affordable bribe, so the attack stops without any fraud having to be detected.
- **Statistical caveat:** values characterise behaviour under the parameter distribution declared in `config.py`, not a universal guarantee.

## Figure 3 --- Chernoff certificate, both directions

- **File:** `fig_03_chernoff_two_sided.png` / `fig_03_chernoff_two_sided.pdf`
- **Purpose:** Two-sided Chernoff certificate: the (1+delta) upper-tail and (1-delta) lower-tail directions validated against the exact value on the same experiment.
- **Variables:** x = Exact P(X>=m); y = Certified bound
- **Observation:** Every one of the 15,000 scenario evaluations receives a certified statement, and the certified interval contains the exact value in 100% of cases. The one-sided bound alone leaves 21-31% of scenarios -- those where the attack is most likely to succeed -- with no analytic statement at all.
- **Statistical caveat:** values characterise behaviour under the parameter distribution declared in `config.py`, not a universal guarantee.

## Figure 4 --- Three-attack comparison

- **File:** `fig_04_attack_comparison.png` / `fig_04_attack_comparison.pdf`
- **Purpose:** Mean success probability for the three vectors, baseline against protected.
- **Variables:** x = System configuration; y = Mean success probability
- **Observation:** All three vectors fall sharply under the protected configuration: bribery 0.350 to 0.064 (81.9%), Sybil 0.480 to 0.136 (71.8%), ballot stuffing 0.442 to 0.116 (73.7%). Sybil attacks remain the most successful of the three, making identity verification the binding weakness.
- **Statistical caveat:** values characterise behaviour under the parameter distribution declared in `config.py`, not a universal guarantee.

## Figure 5 --- Election outcome flip rate

- **File:** `fig_05_election_flip_rate.png` / `fig_05_election_flip_rate.pdf`
- **Purpose:** Probability that an attack flips the winner of a concrete, blockchain-recorded election.
- **Variables:** x = System configuration; y = P(winner flipped)
- **Observation:** On genuinely mined chains with real tallies, baseline flip rates were 44.0% (bribery), 54.7% (Sybil) and 55.0% (ballot stuffing), falling to 1.3%, 11.3% and 8.3% under protection. Chain integrity was never violated in any trial, including the flipped ones.
- **Statistical caveat:** values characterise behaviour under the parameter distribution declared in `config.py`, not a universal guarantee.

## Figure 6 --- Critical detection threshold

- **File:** `fig_06_critical_detection.png` / `fig_06_critical_detection.pdf`
- **Purpose:** Expected attacker utility as detection probability rises, with the critical detection threshold q_d* and the voter-indifference threshold q_v* marked.
- **Variables:** x = q (detection probability); y = Expected attacker utility
- **Observation:** For the medium-organisation scenario the attack stops paying at q_d* = 0.072, well below the q_v* = 0.118 at which voters refuse outright and far below the 0.55 the protected configuration achieves -- so the modelled countermeasures are roughly 8 times stronger than the minimum this scenario requires.
- **Statistical caveat:** values characterise behaviour under the parameter distribution declared in `config.py`, not a universal guarantee.

## Figure 7 --- Binomial distribution and margin thresholds

- **File:** `fig_07_binomial_thresholds.png` / `fig_07_binomial_thresholds.pdf`
- **Purpose:** Binomial outcome distribution with the mean, the manipulation threshold, the attacker-reachable margin and the Chernoff-certified safe margin all marked.
- **Variables:** x = X (surviving fraudulent votes); y = P(X = k)
- **Observation:** The three margin thresholds partition the axis: below m_alpha the attacker wins at even odds, above m_eps the Chernoff bound certifies safety at epsilon = 1e-3, and only the contested band between them requires the exact binomial value.
- **Statistical caveat:** values characterise behaviour under the parameter distribution declared in `config.py`, not a universal guarantee.

## Figure 8 --- Game-theoretic optimal attacker

- **File:** `fig_08_optimal_attacker.png` / `fig_08_optimal_attacker.pdf`
- **Purpose:** Expected attacker utility and flip probability as functions of bribery attempts, with the utility-maximising T* and the even-odds effort threshold marked.
- **Variables:** x = T (bribery attempts); y = Utility (top) / P(flip) (bottom)
- **Observation:** Utility is single-peaked: it rises while additional bribes still move the flip probability, then falls once that probability saturates and each further bribe adds only cost and detection risk. A budget-exhausting attacker therefore does strictly worse than a rational one.
- **Statistical caveat:** values characterise behaviour under the parameter distribution declared in `config.py`, not a universal guarantee.

## Figure 9 --- Vector capacity against the threshold

- **File:** `fig_09_vector_capacity.png` / `fig_09_vector_capacity.pdf`
- **Purpose:** Expected capacity of each vector at full effort, as a multiple of the manipulation threshold, with the optimal coalition's capacity marked.
- **Variables:** x = Benchmark scenario; y = Expected capacity / m
- **Observation:** No single vector has an expected yield reaching the threshold in any scenario: Sybil and ballot-stuffing capacity spans 0.15 to 0.99 of it. Because capacity is a mean rather than a ceiling, success is not impossible below the line -- the best single-vector chance at full effort is 0.42 -- but it is unreliable. The optimal split of one budget across all three clears the line in 4 of 5 scenarios.
- **Statistical caveat:** values characterise behaviour under the parameter distribution declared in `config.py`, not a universal guarantee.

## Figure 10 --- Coalition against best single vector

- **File:** `fig_10_coalition_vs_pure.png` / `fig_10_coalition_vs_pure.pdf`
- **Purpose:** Best coalition attack against best single-vector attack, per scenario, with the protected coalition results overlaid.
- **Variables:** x = Exact success probability; y = Scenario
- **Observation:** The coalition strictly beats the best single vector in 4 of 5 baseline scenarios, raising mean success probability from 0.277 to 0.800. Under protection every coalition result is zero.
- **Statistical caveat:** values characterise behaviour under the parameter distribution declared in `config.py`, not a universal guarantee.

## Figure 11 --- Adversary decision surface

- **File:** `fig_11_adversary_decision_surface.png` / `fig_11_adversary_decision_surface.pdf`
- **Purpose:** Coarse adversary decision surface for baseline attacker utility as a function of budget and detection probability.
- **Variables:** x = Attacker budget B; y = Detection probability q
- **Observation:** The utility surface is most positive for moderate to low detection and sufficiently large budgets, while the budget-to-detection trade-off remains visibly non-linear.
- **Statistical caveat:** values characterise behaviour under the parameter distribution declared in `config.py`, not a universal guarantee.
