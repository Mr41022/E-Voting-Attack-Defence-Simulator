"""
countermeasures/identity_verification.py

Configurable Sybil-identity-verification parameters (thesis section 7).

Baseline vs Protected configurations differ in:
    qs -- probability a fake identity successfully passes registration
    pd -- probability a fake identity is subsequently detected

Protected configuration: lower qs, higher pd (per thesis requirement).
These are simulation parameters, not a claim of perfect verification.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class IdentityVerificationConfig:
    qs: float  # probability a Sybil identity passes registration
    pd: float  # probability a Sybil identity is detected

    @staticmethod
    def baseline(qs: float, pd: float) -> "IdentityVerificationConfig":
        return IdentityVerificationConfig(qs=qs, pd=pd)

    @staticmethod
    def protected(qs_baseline: float, pd_baseline: float,
                   qs_reduction_factor: float, pd_boost_factor: float) -> "IdentityVerificationConfig":
        """Derive a protected configuration from a baseline by reducing
        qs and boosting pd, clamped to [0,1].
        """
        qs_p = max(0.0, min(1.0, qs_baseline * (1 - qs_reduction_factor)))
        pd_p = max(0.0, min(1.0, pd_baseline + (1 - pd_baseline) * pd_boost_factor))
        return IdentityVerificationConfig(qs=qs_p, pd=pd_p)
