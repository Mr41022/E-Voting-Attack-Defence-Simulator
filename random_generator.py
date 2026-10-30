"""
random_generator.py

Single point of reproducible randomness for the whole project, using
numpy.random.Generator (NOT the legacy global np.random state).
"""

from __future__ import annotations
import numpy as np


def make_rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)
