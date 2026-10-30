"""
countermeasures/digital_signatures.py

Conceptual digital-signature verification step. Uses Python's standard
`hashlib` (no invented cryptography) to simulate a signature check as
a boolean pass/fail gate feeding into the overall detection
probability of the ballot-stuffing / bribery pipelines.
"""
from __future__ import annotations
import hashlib


def verify_signature(payload: str, claimed_signature: str) -> bool:
    """Toy signature check: recompute the expected signature hash and
    compare. Standing in for real asymmetric-signature verification,
    which is out of scope for a probabilistic thesis simulation.
    """
    expected = hashlib.sha256((payload + "|sig").encode("utf-8")).hexdigest()
    return expected == claimed_signature
