"""
blockchain_core/block.py

Phase 1 -- Blockchain Foundation: Block structure.

Each block contains:
    index          -- position in the chain
    timestamp       -- ISO-8601 UTC creation time
    votes           -- list of vote-transaction dicts sealed into this block
    previous_hash   -- hash of the preceding block (chain linkage)
    nonce           -- proof-of-work nonce
    hash            -- SHA-256 hash of this block's contents

This is an educational, single-process blockchain (no peer-to-peer
networking or real distributed consensus) built for a synthetic
e-voting research simulation. It uses Python's standard `hashlib`
(SHA-256) -- no invented cryptography.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any
import hashlib
import json


@dataclass
class Block:
    index: int
    timestamp: str
    votes: List[Dict[str, Any]]
    previous_hash: str
    nonce: int = 0
    hash: str = ""

    def votes_digest(self) -> str:
        """SHA-256 digest of this block's CURRENT vote list, recomputed
        fresh from self.votes every call (no caching) -- this is what
        makes tamper detection reliable: if `votes` is edited after the
        fact (see Blockchain.tamper_with_block), the very next call to
        votes_digest()/compute_hash() reflects the edited data, so a
        stale cached digest can never mask tampering. Mirrors a real
        blockchain's Merkle-root pattern: transaction data is condensed
        to a fixed-size digest that feeds into the block header hash.
        """
        votes_string = json.dumps(self.votes, sort_keys=True, default=str)
        return hashlib.sha256(votes_string.encode("utf-8")).hexdigest()

    def header_hash(self, votes_digest: str) -> str:
        """Hashes the block HEADER only (index, timestamp, votes_digest,
        previous_hash, nonce) given an already-computed votes digest.
        Used by the proof-of-work search loop so that only the small,
        fixed-size header needs rehashing on every nonce attempt --
        the (potentially large) vote list is hashed once per block,
        not once per nonce attempt.
        """
        header = {
            "index": self.index,
            "timestamp": self.timestamp,
            "votes_digest": votes_digest,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
        }
        header_string = json.dumps(header, sort_keys=True, default=str)
        return hashlib.sha256(header_string.encode("utf-8")).hexdigest()

    def compute_hash(self) -> str:
        """hash = SHA256(index + timestamp + votes + previousHash + nonce),
        with the vote list condensed to its digest first purely as a
        mining/verification performance optimisation (see votes_digest
        docstring) -- tampering with any vote still changes the digest,
        still changes this hash, and is still caught by chain
        validation. Always recomputes the digest fresh from self.votes,
        so this is safe to call at any time (mining, validation, or
        after a deliberate tamper) and will always reflect the block's
        current, possibly-tampered contents.
        """
        return self.header_hash(self.votes_digest())

    @staticmethod
    def new(index: int, votes: List[Dict[str, Any]], previous_hash: str) -> "Block":
        return Block(
            index=index,
            timestamp=datetime.now(timezone.utc).isoformat(),
            votes=votes,
            previous_hash=previous_hash,
            nonce=0,
            hash="",
        )
