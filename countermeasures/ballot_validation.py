"""
countermeasures/ballot_validation.py

Configurable ballot-stuffing countermeasure parameters (thesis section 9).

    qb -- probability a fraudulent ballot is accepted
    pb -- probability a fraudulent ballot is detected

Protected configuration: lower qb, higher pb, representing digital
signatures + eligibility checks + duplicate detection + blockchain
transaction validation + immutable audit records, modelled purely as
probability adjustments (no claim of perfect prevention).
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class BallotValidationConfig:
    qb: float
    pb: float

    @staticmethod
    def baseline(qb: float, pb: float) -> "BallotValidationConfig":
        return BallotValidationConfig(qb=qb, pb=pb)

    @staticmethod
    def protected(qb_baseline: float, pb_baseline: float,
                   qb_reduction_factor: float, pb_boost_factor: float) -> "BallotValidationConfig":
        qb_p = max(0.0, min(1.0, qb_baseline * (1 - qb_reduction_factor)))
        pb_p = max(0.0, min(1.0, pb_baseline + (1 - pb_baseline) * pb_boost_factor))
        return BallotValidationConfig(qb=qb_p, pb=pb_p)
