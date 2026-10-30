"""
evoting_app/entities.py

Phase 2 -- E-Voting System: core entities (Module 1-4 of the spec).

All identities are synthetic and created only in-memory for this
simulation -- no real people, credentials, or elections are involved.
Passwords are stored as SHA-256 hashes purely for structural realism
(demonstrating that plaintext passwords are never kept); this is a
research simulation, not a production authentication system.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
import hashlib


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


@dataclass
class User:
    """Module 1 -- User Authentication base class."""
    user_id: str
    name: str
    email: str
    password_hash: str
    role: str  # "admin" | "voter"

    @staticmethod
    def create(user_id: str, name: str, email: str, password: str, role: str) -> "User":
        return User(user_id=user_id, name=name, email=email,
                     password_hash=_hash_password(password), role=role)

    def check_password(self, password: str) -> bool:
        return self.password_hash == _hash_password(password)


@dataclass
class Admin(User):
    pass


@dataclass
class Voter(User):
    """Module 4 -- Voter Registration record."""
    has_voted: Dict[str, bool] = field(default_factory=dict)  # election_id -> bool

    def has_voted_in(self, election_id: str) -> bool:
        return self.has_voted.get(election_id, False)

    def mark_voted(self, election_id: str) -> None:
        self.has_voted[election_id] = True


@dataclass
class Candidate:
    """Module 3 -- Candidate Management."""
    candidate_id: str
    name: str
    party: str
    election_id: str
    photo: Optional[str] = None


@dataclass
class Election:
    """Module 2 -- Election Management."""
    election_id: str
    name: str
    start_date: str
    end_date: str
    status: str = "created"  # "created" | "active" | "ended"
    candidate_ids: List[str] = field(default_factory=list)

    def start(self) -> None:
        self.status = "active"

    def end(self) -> None:
        self.status = "ended"

    def is_active(self) -> bool:
        return self.status == "active"
