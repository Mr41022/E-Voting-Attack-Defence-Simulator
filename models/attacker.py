"""
models/attacker.py

M3: T = min(N, floor(B/R)),  where mathematically valid and R > 0.

Handles B=0, R=0, B<R explicitly rather than raising or silently
defaulting to a nonsensical T.
"""

from __future__ import annotations
from dataclasses import dataclass
import math


@dataclass
class AttackerBudget:
    N: int
    B: float  # total bribery budget
    R: float  # reward per voter

    def max_targets(self) -> int:
        """M3: T = min(N, floor(B/R))

        - R == 0: reward is meaningless (no offer being made); no
          voter can rationally be "bought" with a zero reward under
          this model's bookkeeping, so T = 0.
        - B == 0: no budget, T = 0.
        - B < R: cannot afford even a single briber, T = 0.
        - N <= 0: no electorate to target, T = 0.
        """
        if self.N <= 0 or self.R <= 0 or self.B <= 0:
            return 0
        T = min(self.N, math.floor(self.B / self.R))
        return max(0, int(T))
