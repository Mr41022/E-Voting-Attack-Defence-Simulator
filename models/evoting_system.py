"""
models/evoting_system.py

A CONCRETE synthetic e-voting system: a two-candidate election whose
ballots are processed through the simulated blockchain ledger and
audit log (countermeasures/blockchain.py, countermeasures/audit.py).
This is what the three attacks (bribery, Sybil, ballot stuffing)
actually attack, and what the countermeasures actually defend, in a
way that produces a concrete outcome (a winner, a vote tally) rather
than only an abstract success probability.

No real candidates, parties, or elections are modelled. "Candidate A"
and "Candidate B" are generic synthetic labels with no real-world
referent.

Key idea tying this to the abstract framework in attacks/*.py: the
manipulation threshold `m` used throughout the rest of the project is,
concretely, exactly the number of additional fraudulent votes needed
to overturn THIS election's result (`flip_threshold` below). "Attack
success" (X >= m) is therefore exactly "the wrong candidate wins."
"""

from __future__ import annotations
from dataclasses import dataclass
import numpy as np

from countermeasures.blockchain import SimulatedLedger
from countermeasures.audit import AuditLog


@dataclass
class ElectionResult:
    votes_A: int
    votes_B: int
    winner: str  # "A" | "B" | "tie"
    margin: int


def cast_legitimate_votes(N: int, support_B: float, rng: np.random.Generator,
                           ledger: SimulatedLedger | None = None,
                           audit: AuditLog | None = None,
                           trial_id: int = 0,
                           log_individual_ballots: bool = False) -> ElectionResult:
    """N legitimate synthetic voters each cast one ballot: Bernoulli(support_B)
    for Candidate B, else Candidate A. Legitimate ballots always pass
    validation in this model (fraud detection applies only to
    attacker-injected ballots/identities, modelled separately in
    simulate_fraud_attempts below) -- this mirrors real systems, where
    the validation pipeline exists to catch fraud, not to reject
    genuine voters.

    If a ledger/audit log is supplied, every ballot is recorded as an
    accepted transaction (log_individual_ballots=True) or a single
    aggregate audit entry (default, to keep large-N runs fast).
    """
    ballots = (rng.random(N) < support_B).astype(int)
    votes_B = int(ballots.sum())
    votes_A = N - votes_B

    if ledger is not None and log_individual_ballots:
        for i in range(N):
            candidate = "B" if ballots[i] == 1 else "A"
            ledger.record(f"legit-{trial_id}-{i}", f"voter-{trial_id}-{i}", candidate,
                           "accepted", "legitimate ballot")
    if audit is not None:
        audit.log(trial_id, "election", "VOTE_VALIDATED", "accepted",
                   f"{N} legitimate ballots recorded ({votes_A} for A, {votes_B} for B)", "n/a")

    winner = "A" if votes_A > votes_B else ("B" if votes_B > votes_A else "tie")
    margin = abs(votes_A - votes_B)
    return ElectionResult(votes_A=votes_A, votes_B=votes_B, winner=winner, margin=margin)


def flip_threshold(result: ElectionResult, target: str) -> int:
    """Minimum number of ADDITIONAL fraudulent votes for `target` needed
    to overtake the current winner, assuming fraudulent votes are
    newly injected in favour of `target` only (not converted from the
    opponent's existing tally -- the standard, more conservative
    assumption for bribery/Sybil/ballot-stuffing, since those attacks
    add new fraudulent ballots rather than altering cast ones).

    This is the concrete instantiation of the abstract manipulation
    threshold `m` used throughout mathematics/ and attacks/.
    """
    if target not in ("A", "B"):
        raise ValueError("target must be 'A' or 'B'")
    opponent_votes = result.votes_A if target == "B" else result.votes_B
    target_votes = result.votes_B if target == "B" else result.votes_A
    if target_votes > opponent_votes:
        return 0  # already winning; no manipulation needed
    return (opponent_votes - target_votes) + 1


def simulate_fraud_attempts(n_attempts: int, accept_prob: float, detect_prob: float,
                             rng: np.random.Generator):
    """Simulate n_attempts individual fraudulent-vote attempts.

    accept_prob: probability a single attempt is accepted into the
        system (for bribery this is 1.0 -- every bribe a rational
        voter accepts IS cast; for Sybil/ballot stuffing this is
        qs/qb, the registration/acceptance probability).
    detect_prob: probability an accepted fraudulent vote is
        subsequently detected (q for bribery, pd for Sybil, pb for
        ballot stuffing).

    Returns (n_accepted, n_detected, n_surviving, accepted_mask,
    detected_mask, surviving_mask). "Surviving" = accepted AND not
    detected -- the count that actually lands in the final tally.
    """
    if n_attempts <= 0:
        empty = np.zeros(0, dtype=bool)
        return 0, 0, 0, empty, empty, empty

    accepted = rng.random(n_attempts) < accept_prob
    n_accepted = int(accepted.sum())
    detected = np.zeros(n_attempts, dtype=bool)
    if n_accepted > 0:
        detect_draw = rng.random(n_accepted) < detect_prob
        detected[np.where(accepted)[0]] = detect_draw
    surviving = accepted & (~detected)
    return int(accepted.sum()), int(detected.sum()), int(surviving.sum()), accepted, detected, surviving


def apply_fraudulent_votes(result: ElectionResult, target: str, surviving_fraud_votes: int) -> ElectionResult:
    """Add the SURVIVING (accepted and undetected) fraudulent votes to
    `target`'s tally and recompute the winner -- the concrete,
    post-attack, post-countermeasure election outcome.
    """
    votes_A = result.votes_A + (surviving_fraud_votes if target == "A" else 0)
    votes_B = result.votes_B + (surviving_fraud_votes if target == "B" else 0)
    winner = "A" if votes_A > votes_B else ("B" if votes_B > votes_A else "tie")
    margin = abs(votes_A - votes_B)
    return ElectionResult(votes_A=votes_A, votes_B=votes_B, winner=winner, margin=margin)
