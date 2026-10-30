"""
blockchain_core/chain.py

Phase 1 -- Blockchain Foundation: the Blockchain class.

Responsibilities (per project spec):
    - create_genesis_block()
    - mine_block() / mine_pending_votes()
    - add_block()
    - is_chain_valid()
    - replace_chain()

Proof of work: mining requires finding a nonce such that the block's
hash starts with a configurable number of leading zero hex digits
(the "difficulty"). Difficulty defaults to 3 ("000...") so that mining
completes near-instantly in a research/demo context while still
genuinely demonstrating the search-for-nonce mechanic -- a real
production chain would use a much higher difficulty.

Tampering detection: if any vote inside any block is altered after
the fact, that block's stored hash no longer matches
`block.compute_hash()`, which is caught by `is_chain_valid()`; because
each block also stores the previous block's hash, altering one block
breaks the linkage for every subsequent block too.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import copy

from blockchain_core.block import Block


@dataclass
class ValidationResult:
    valid: bool
    first_invalid_index: Optional[int]
    reason: str


class Blockchain:
    def __init__(self, difficulty: int = 3):
        self.difficulty = difficulty
        self.chain: List[Block] = []
        self.pending_votes: List[Dict[str, Any]] = []
        self.create_genesis_block()

    # ------------------------------------------------------------------
    # Chain construction
    # ------------------------------------------------------------------
    def create_genesis_block(self) -> Block:
        genesis = Block.new(index=0, votes=[], previous_hash="0" * 64)
        genesis.hash = self._proof_of_work(genesis)
        self.chain.append(genesis)
        return genesis

    @property
    def last_block(self) -> Block:
        return self.chain[-1]

    def _proof_of_work(self, block: Block) -> str:
        """Search for a nonce such that the resulting hash starts with
        `self.difficulty` leading zeros -- the literal 'mining requires
        finding a nonce such that hash starts with 0000...' requirement.

        Performance note: the (potentially large) vote list is hashed
        into a digest ONCE before the search begins; each nonce attempt
        then only rehashes the small, fixed-size block header (see
        Block.header_hash), so mining time does not scale with the
        number of votes sealed into the block.
        """
        target_prefix = "0" * self.difficulty
        votes_digest = block.votes_digest()  # computed once, not per-nonce
        block.nonce = 0
        computed = block.header_hash(votes_digest)
        while not computed.startswith(target_prefix):
            block.nonce += 1
            computed = block.header_hash(votes_digest)
        return computed

    def add_vote_to_pending(self, vote: Dict[str, Any]) -> None:
        self.pending_votes.append(vote)

    def mine_block(self) -> Block:
        """mineBlock(): seals all currently pending votes into a new
        block, performs proof-of-work, appends it to the chain, and
        clears the pending pool.
        """
        new_block = Block.new(
            index=self.last_block.index + 1,
            votes=list(self.pending_votes),
            previous_hash=self.last_block.hash,
        )
        new_block.hash = self._proof_of_work(new_block)
        self.chain.append(new_block)
        self.pending_votes = []
        return new_block

    def add_block(self, block: Block) -> bool:
        """addBlock(): appends an externally-constructed, already-mined
        block, provided it correctly links to the current chain tip.
        Used by replace_chain() / for demonstrating chain adoption.
        """
        if block.previous_hash != self.last_block.hash:
            return False
        if block.hash != block.compute_hash():
            return False
        if not block.hash.startswith("0" * self.difficulty):
            return False
        self.chain.append(block)
        return True

    # ------------------------------------------------------------------
    # Validation / tamper detection
    # ------------------------------------------------------------------
    def is_chain_valid(self, chain: Optional[List[Block]] = None) -> ValidationResult:
        """isChainValid(): walks the chain from genesis, checking (a)
        each block's stored hash matches a fresh recomputation of its
        contents (catches tampering with vote data), (b) each block's
        previous_hash correctly links to the prior block's hash (catches
        reordering/splicing), and (c) each hash still satisfies the
        proof-of-work difficulty target.
        """
        target = chain if chain is not None else self.chain
        if not target:
            return ValidationResult(False, None, "Chain is empty.")

        for i, block in enumerate(target):
            recomputed = block.compute_hash()
            if recomputed != block.hash:
                return ValidationResult(False, i,
                                         f"Block {i} hash mismatch -- stored hash does not match "
                                         f"recomputed hash. Vote data has been tampered with.")
            if i > 0 and block.previous_hash != target[i - 1].hash:
                return ValidationResult(False, i,
                                         f"Block {i} previous_hash does not match block {i-1}'s hash "
                                         f"-- chain linkage broken.")
            if not block.hash.startswith("0" * self.difficulty):
                return ValidationResult(False, i,
                                         f"Block {i} hash does not satisfy proof-of-work difficulty "
                                         f"{self.difficulty}.")
        return ValidationResult(True, None, "Chain is valid.")

    def replace_chain(self, new_chain: List[Block]) -> bool:
        """replaceChain(): adopts `new_chain` only if it is valid and
        at least as long as the current chain (longest-valid-chain
        rule, the standard simulated-consensus mechanism for this
        educational single-process blockchain).
        """
        if len(new_chain) < len(self.chain):
            return False
        result = self.is_chain_valid(new_chain)
        if not result.valid:
            return False
        self.chain = list(new_chain)
        return True

    # ------------------------------------------------------------------
    # Demonstration helper
    # ------------------------------------------------------------------
    def tamper_with_block(self, index: int, new_votes: List[Dict[str, Any]]) -> None:
        """Directly overwrites a block's vote data WITHOUT re-mining --
        i.e. simulates an attacker editing history outside the
        legitimate mine_block() path. The block's stored `hash` field
        is deliberately left unchanged, so is_chain_valid() will catch
        the mismatch. This method exists purely to demonstrate tamper
        detection (see demo_blockchain_evoting.py Phase 1 demo) and is
        never called as part of the legitimate voting flow.
        """
        if index < 0 or index >= len(self.chain):
            raise IndexError("Block index out of range.")
        self.chain[index] = copy.deepcopy(self.chain[index])
        self.chain[index].votes = new_votes

    # ------------------------------------------------------------------
    # Vote counting (traverses the chain from genesis)
    # ------------------------------------------------------------------
    def count_votes(self) -> Dict[str, int]:
        """Traverses Genesis -> Block 1 -> Block 2 -> ... and tallies
        candidate_id occurrences across every sealed vote transaction.
        """
        tally: Dict[str, int] = {}
        for block in self.chain:
            for vote in block.votes:
                candidate_id = vote.get("candidate_id")
                if candidate_id is None:
                    continue
                tally[candidate_id] = tally.get(candidate_id, 0) + 1
        return tally
