"""
simulation/election_attack_runner.py

Runs paired baseline/protected trials on a CONCRETE two-candidate
election recorded on the REAL proof-of-work blockchain
(blockchain_core/chain.py) -- not an abstract probability model.

Pipeline per trial, matching the validation pipeline used throughout
the project (submit -> eligibility/acceptance check -> detection check
-> blockchain recording):

    1. A legitimate electorate casts ballots; every legitimate ballot
       is accepted and sealed into the chain in a single mined block
       (batch mining -- one proof-of-work per trial for the legitimate
       vote batch, which is what a real system's block interval would
       look like, rather than one block per voter).
    2. The current winner/loser is read directly from the mined chain
       via Blockchain.count_votes() (i.e. the "pre-attack" tally is a
       genuine blockchain read, not a Python-side running total).
    3. An attacker targets the losing candidate and attempts bribery /
       Sybil / ballot-stuffing fraud. Each fraudulent vote is
       individually simulated as accepted-or-rejected (registration /
       bribe-acceptance gate) and, if accepted, detected-or-undetected
       (the security/countermeasure gate). ONLY votes that are
       accepted AND undetected are sealed into the chain -- exactly
       mirroring the "Vote submitted -> validation -> detection ->
       blockchain recording" pipeline. Detected/rejected fraud is
       logged but never reaches the ledger, matching real
       countermeasure behaviour (a rejected transaction is not
       recorded as a cast vote).
    4. The post-attack tally is again read directly from the mined
       chain, and the chain's own is_chain_valid() is checked to
       confirm the ledger itself remains internally consistent even
       while under attack (attacks succeed or fail at the validation
       gate BEFORE mining, not by corrupting already-mined blocks --
       that latter scenario is what Phase 1's tamper-detection demo
       covers separately in demo_blockchain_evoting.py).

For performance across many trials, this module calls
blockchain_core.Blockchain directly (batch-mining) rather than the
full evoting_app.VotingService (which adds per-voter registration/
duplicate-vote bookkeeping intended for the small worked-example demo
in demo_blockchain_evoting.py). Both sit on the identical Phase-1
Blockchain class, so the underlying ledger mechanics are identical.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, List
import copy
import numpy as np
import pandas as pd

from blockchain_core.chain import Blockchain
from models.evoting_system import simulate_fraud_attempts
from mathematics.utility import rational_voter_decision
from models.attacker import AttackerBudget


@dataclass
class ElectionAttackOutcome:
    trial_id: int
    attack_type: str
    system_type: str
    N: int
    support_B: float
    pre_votes_A: int
    pre_votes_B: int
    pre_winner: str
    pre_margin: int
    target_candidate: str
    m_flip_threshold: int
    attempted: int
    accepted: int
    detected: int
    surviving: int
    post_votes_A: int
    post_votes_B: int
    post_winner: str
    flipped: bool
    attacker_cost: float
    chain_valid_after_attack: bool

    def as_dict(self) -> Dict:
        return asdict(self)


def _flip_threshold(votes_A: int, votes_B: int, target: str) -> int:
    opponent = votes_A if target == "B" else votes_B
    mine = votes_B if target == "B" else votes_A
    if mine > opponent:
        return 0
    return (opponent - mine) + 1


def _mine_legit_votes(N: int, support_B: float, rng: np.random.Generator, trial_id: int):
    """Batch-mines N legitimate ballots into a single block on a fresh
    Blockchain instance (each trial gets its own chain -- a fresh
    election). Returns (blockchain, votes_A, votes_B).
    """
    bc = Blockchain(difficulty=3)
    ballots = rng.random(N) < support_B  # True = vote for B
    for i in range(N):
        candidate = "B" if ballots[i] else "A"
        bc.add_vote_to_pending({
            "vote_id": f"legit-{trial_id}-{i}",
            "voter_id": f"voter-{trial_id}-{i}",
            "candidate_id": candidate,
            "election_id": f"election-{trial_id}",
        })
    bc.mine_block()
    tally = bc.count_votes()
    return bc, tally.get("A", 0), tally.get("B", 0)


def _mine_fraud_votes(bc: Blockchain, target: str, surviving: int, trial_id: int, attack_type: str):
    """Seals exactly `surviving` fraudulent votes for `target` into a
    new block -- these are the fraud attempts that passed BOTH the
    acceptance gate and the detection gate. Rejected/detected attempts
    are never added to pending and therefore never reach the chain,
    matching real validation-pipeline behaviour.
    """
    for i in range(surviving):
        bc.add_vote_to_pending({
            "vote_id": f"{attack_type}-{trial_id}-{i}",
            "voter_id": f"fraud-{attack_type}-{trial_id}-{i}",
            "candidate_id": target,
            "election_id": f"election-{trial_id}",
        })
    if surviving > 0:
        bc.mine_block()
    return bc


def run_election_attack_trials(n_trials: int, seed: int) -> pd.DataFrame:
    """Runs n_trials concrete elections, each attacked by all three
    attack types under both baseline and protected configurations,
    with every accepted-and-undetected fraudulent vote genuinely mined
    into a real proof-of-work blockchain. Returns the results
    DataFrame (one row per trial x attack_type x system_type).
    """
    master_rng = np.random.default_rng(seed)
    trial_seeds = master_rng.integers(0, 2**32 - 1, size=n_trials)
    rows: List[Dict] = []

    for i in range(n_trials):
        trial_id = i + 1
        rng = np.random.default_rng(int(trial_seeds[i]))

        N = int(rng.integers(150, 900))
        support_B = float(rng.uniform(0.35, 0.65))  # biased toward close races

        # ---- legitimate electorate, mined once into the real chain ----
        base_bc, pre_A, pre_B = _mine_legit_votes(N, support_B, rng, trial_id)
        pre_winner = "A" if pre_A > pre_B else ("B" if pre_B > pre_A else "tie")
        pre_margin = abs(pre_A - pre_B)
        target = "B" if pre_winner in ("A", "tie") else "A"
        m = _flip_threshold(pre_A, pre_B, target)

        # ---- shared per-trial attacker resource draws (paired across attack types) ----
        B_budget = float(rng.uniform(2000, 40000))
        R = float(rng.uniform(20, 300))
        P = float(rng.uniform(50, 1500))
        q_baseline = float(rng.uniform(0.02, 0.20))
        q_protected = min(1.0, q_baseline + (1 - q_baseline) * rng.uniform(0.35, 0.75))

        S = int(rng.integers(5, 300))
        qs_baseline = float(rng.uniform(0.5, 0.9))
        qs_protected = max(0.0, qs_baseline * (1 - rng.uniform(0.4, 0.8)))
        pd_baseline = float(rng.uniform(0.02, 0.20))
        pd_protected = min(1.0, pd_baseline + (1 - pd_baseline) * rng.uniform(0.35, 0.75))

        A_ = int(rng.integers(5, 300))
        qb_baseline = float(rng.uniform(0.4, 0.85))
        qb_protected = max(0.0, qb_baseline * (1 - rng.uniform(0.4, 0.8)))
        pb_baseline = float(rng.uniform(0.02, 0.20))
        pb_protected = min(1.0, pb_baseline + (1 - pb_baseline) * rng.uniform(0.35, 0.75))

        attacker = AttackerBudget(N=N, B=B_budget, R=R)
        T = attacker.max_targets()

        attack_configs = {
            "bribery": [("baseline", q_baseline), ("protected", q_protected)],
            "sybil": [("baseline", (qs_baseline, pd_baseline)), ("protected", (qs_protected, pd_protected))],
            "ballot_stuffing": [("baseline", (qb_baseline, pb_baseline)), ("protected", (qb_protected, pb_protected))],
        }

        for attack_type, configs in attack_configs.items():
            for system_type, params in configs:
                # Each (attack_type, system_type) combo attacks an
                # independent COPY of the post-legitimate-vote chain
                # state, so the three attacks/configs are evaluated
                # against the identical starting tally (paired design)
                # rather than compounding on each other.
                bc = copy.deepcopy(base_bc)

                if attack_type == "bribery":
                    q = params
                    decision = rational_voter_decision(q, R, P)
                    n_attempts = T if decision.accepts else 0
                    accepted_n, detected_n, surviving_n, *_ = simulate_fraud_attempts(
                        n_attempts, accept_prob=1.0, detect_prob=q, rng=rng)
                    attacker_cost = accepted_n * R
                elif attack_type == "sybil":
                    qs, pdv = params
                    accepted_n, detected_n, surviving_n, *_ = simulate_fraud_attempts(
                        S, accept_prob=qs, detect_prob=pdv, rng=rng)
                    n_attempts = S
                    attacker_cost = float("nan")
                else:  # ballot_stuffing
                    qb, pbv = params
                    accepted_n, detected_n, surviving_n, *_ = simulate_fraud_attempts(
                        A_, accept_prob=qb, detect_prob=pbv, rng=rng)
                    n_attempts = A_
                    attacker_cost = float("nan")

                _mine_fraud_votes(bc, target, surviving_n, trial_id, attack_type)
                post_tally = bc.count_votes()
                post_A, post_B = post_tally.get("A", 0), post_tally.get("B", 0)
                post_winner = "A" if post_A > post_B else ("B" if post_B > post_A else "tie")
                chain_ok = bc.is_chain_valid().valid

                rows.append(ElectionAttackOutcome(
                    trial_id=trial_id, attack_type=attack_type, system_type=system_type,
                    N=N, support_B=support_B,
                    pre_votes_A=pre_A, pre_votes_B=pre_B, pre_winner=pre_winner, pre_margin=pre_margin,
                    target_candidate=target, m_flip_threshold=m,
                    attempted=n_attempts, accepted=accepted_n, detected=detected_n, surviving=surviving_n,
                    post_votes_A=post_A, post_votes_B=post_B, post_winner=post_winner,
                    flipped=(post_winner == target and pre_winner != target),
                    attacker_cost=attacker_cost,
                    chain_valid_after_attack=chain_ok,
                ).as_dict())

    return pd.DataFrame(rows)
