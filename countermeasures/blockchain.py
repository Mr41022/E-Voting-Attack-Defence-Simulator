"""
countermeasures/blockchain.py

Simulated, educational immutable-ledger abstraction. This is NOT a
cryptocurrency and does not implement peer-to-peer consensus or a real
distributed network -- it is a conceptual audit-record store used to
demonstrate how a validation pipeline and immutable audit trail can
raise detection probability for fraudulent actions.

Pipeline (conceptual, per thesis section 3):
    submit -> eligibility check -> signature check -> duplicate check
    -> transaction validation -> ledger record -> audit log entry
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any
import hashlib


@dataclass
class LedgerRecord:
    vote_id: str
    synthetic_voter_id: str
    candidate: str
    timestamp: str
    signature_hash: str
    tx_hash: str
    status: str  # "accepted" | "rejected" | "detected"
    reason: str


class SimulatedLedger:
    """In-memory append-only list standing in for a blockchain ledger.
    Uses SHA-256 (a standard, well-established hash function -- no
    invented cryptography) purely to produce a deterministic
    "transaction hash" string for audit-record realism.
    """

    def __init__(self):
        self._records: List[LedgerRecord] = []

    def record(self, vote_id: str, synthetic_voter_id: str, candidate: str,
               status: str, reason: str) -> LedgerRecord:
        ts = datetime.now(timezone.utc).isoformat()
        payload = f"{vote_id}|{synthetic_voter_id}|{candidate}|{ts}|{status}"
        tx_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        sig_hash = hashlib.sha256((payload + "|sig").encode("utf-8")).hexdigest()
        rec = LedgerRecord(vote_id, synthetic_voter_id, candidate, ts,
                            sig_hash, tx_hash, status, reason)
        self._records.append(rec)
        return rec

    def summary(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for r in self._records:
            out[r.status] = out.get(r.status, 0) + 1
        return out

    def all_records(self) -> List[LedgerRecord]:
        return list(self._records)
