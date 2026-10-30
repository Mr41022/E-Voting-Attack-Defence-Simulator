import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from countermeasures.identity_verification import IdentityVerificationConfig
from countermeasures.ballot_validation import BallotValidationConfig
from countermeasures.blockchain import SimulatedLedger


def test_identity_protected_stronger_than_baseline():
    base = IdentityVerificationConfig.baseline(qs=0.8, pd=0.1)
    prot = IdentityVerificationConfig.protected(0.8, 0.1, qs_reduction_factor=0.5, pd_boost_factor=0.5)
    assert prot.qs < base.qs
    assert prot.pd > base.pd


def test_ballot_protected_stronger_than_baseline():
    base = BallotValidationConfig.baseline(qb=0.7, pb=0.1)
    prot = BallotValidationConfig.protected(0.7, 0.1, qb_reduction_factor=0.4, pb_boost_factor=0.4)
    assert prot.qb < base.qb
    assert prot.pb > base.pb


def test_ledger_records_and_summarises():
    ledger = SimulatedLedger()
    ledger.record("v1", "syn-1", "A", "accepted", "ok")
    ledger.record("v2", "syn-2", "B", "rejected", "duplicate")
    s = ledger.summary()
    assert s["accepted"] == 1
    assert s["rejected"] == 1
