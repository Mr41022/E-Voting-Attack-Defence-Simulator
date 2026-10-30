"""
models/voter.py

Rational voter wrapper around mathematics/utility.py's decision rule.
Represents a synthetic voter targeted by a bribery attempt. No real
identity or personal data is modelled -- only the parameters required
by the utility function (q, R, P).
"""

from __future__ import annotations
from dataclasses import dataclass
from mathematics.utility import rational_voter_decision, VoterDecision


@dataclass
class Voter:
    voter_index: int  # synthetic index only, not a real identity

    def decide(self, q: float, R: float, P: float) -> VoterDecision:
        return rational_voter_decision(q, R, P)
