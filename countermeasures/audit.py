"""
countermeasures/audit.py

Structured audit-log record generation (thesis section 17). No
personally identifying information is stored -- only synthetic trial
and event metadata.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Dict, Any


@dataclass
class AuditRecord:
    timestamp: str
    trial_id: int
    attack_type: str
    event_type: str
    status: str
    reason: str
    security_configuration: str

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AuditLog:
    def __init__(self):
        self._records: List[AuditRecord] = []

    def log(self, trial_id: int, attack_type: str, event_type: str,
             status: str, reason: str, security_configuration: str) -> None:
        rec = AuditRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            trial_id=trial_id,
            attack_type=attack_type,
            event_type=event_type,
            status=status,
            reason=reason,
            security_configuration=security_configuration,
        )
        self._records.append(rec)

    def records(self) -> List[AuditRecord]:
        return list(self._records)

    def counts_by_event(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for r in self._records:
            out[r.event_type] = out.get(r.event_type, 0) + 1
        return out
