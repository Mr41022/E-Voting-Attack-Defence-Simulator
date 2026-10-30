"""
models/election.py

Core election-scenario parameters shared by all three attack models.
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class ElectionScenario:
    """N = electorate size, m = manipulation threshold (min. successful
    fraudulent actions needed to change the outcome). 0 < m < N is the
    "typical" assumption, but the code tolerates m<=0 and m>N as
    explicit edge cases (see mathematics/binomial.py).
    """
    N: int
    m: int
    trial_id: int
    seed: int

    def validate(self) -> list[str]:
        notes = []
        if self.N <= 0:
            notes.append("N <= 0: degenerate electorate.")
        if self.m <= 0:
            notes.append("m <= 0: any nonzero manipulation trivially succeeds.")
        if self.m > self.N:
            notes.append("m > N: manipulation threshold exceeds electorate size; attack is impossible by definition.")
        return notes
