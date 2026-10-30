"""
evoting_app/service.py

Phase 2/3 -- E-Voting System service layer + final integration.

Implements Modules 1-8 of the spec on top of the Phase-1 blockchain:
    Module 1: User Authentication          -> register_admin / register_voter / login
    Module 2: Election Management          -> create_election / start_election / end_election
    Module 3: Candidate Management         -> add_candidate
    Module 4: Voter Registration           -> register_voter
    Module 5: Vote Casting                 -> cast_vote (full flow)
    Module 6: Duplicate Vote Prevention    -> cast_vote checks has_voted_in()
    Module 7: Blockchain Storage           -> cast_vote -> pending -> mine_block()
    Module 8: Vote Counting                -> publish_results (traverses the chain)

Complete workflow (Phase 3):
    register voter -> admin login -> create election -> add candidates
    -> start election -> voter login -> select candidate -> vote created
    -> vote stored -> mine block -> blockchain updated -> hash verified
    -> vote count -> result published
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from blockchain_core.chain import Blockchain
from evoting_app.entities import User, Admin, Voter, Candidate, Election


class VotingServiceError(Exception):
    """Raised for any rejected operation (auth failure, duplicate vote,
    inactive election, unknown candidate, etc). Carries a human-readable
    reason so the demo/report can show *why* an action was rejected.
    """


@dataclass
class VoteReceipt:
    vote_id: str
    voter_id: str
    candidate_id: str
    election_id: str
    block_index: int
    block_hash: str


class VotingService:
    def __init__(self, difficulty: int = 3):
        self.blockchain = Blockchain(difficulty=difficulty)
        self.users: Dict[str, User] = {}
        self.elections: Dict[str, Election] = {}
        self.candidates: Dict[str, Candidate] = {}
        self._vote_counter = 0

    def _require_admin(self, admin: Admin) -> None:
        registered = self.users.get(getattr(admin, "user_id", None))
        if not isinstance(admin, Admin) or admin.role != "admin" or registered is not admin:
            raise VotingServiceError("Only a registered administrator can perform this operation.")

    def _require_voter(self, voter: Voter) -> None:
        registered = self.users.get(getattr(voter, "user_id", None))
        if not isinstance(voter, Voter) or voter.role != "voter" or registered is not voter:
            raise VotingServiceError("Only a registered voter can cast a vote.")

    # ---------------- Module 1: User Authentication ----------------
    def register_admin(self, user_id: str, name: str, email: str, password: str) -> Admin:
        if user_id in self.users:
            raise VotingServiceError(f"User ID '{user_id}' is already registered.")
        admin = Admin(user_id=user_id, name=name, email=email,
                      password_hash=User.create(user_id, name, email, password, "admin").password_hash,
                      role="admin")
        self.users[user_id] = admin
        return admin

    def register_voter(self, user_id: str, name: str, email: str, password: str) -> Voter:
        if user_id in self.users:
            raise VotingServiceError(f"User ID '{user_id}' is already registered.")
        voter = Voter(user_id=user_id, name=name, email=email,
                       password_hash=User.create(user_id, name, email, password, "voter").password_hash,
                       role="voter")
        self.users[user_id] = voter
        return voter

    def login(self, user_id: str, password: str) -> User:
        user = self.users.get(user_id)
        if user is None or not user.check_password(password):
            raise VotingServiceError("Invalid credentials.")
        return user

    # ---------------- Module 2: Election Management ----------------
    def create_election(self, admin: Admin, election_id: str, name: str,
                         start_date: str, end_date: str) -> Election:
        self._require_admin(admin)
        if election_id in self.elections:
            raise VotingServiceError(f"Election ID '{election_id}' is already registered.")
        election = Election(election_id=election_id, name=name,
                             start_date=start_date, end_date=end_date, status="created")
        self.elections[election_id] = election
        return election

    def start_election(self, admin: Admin, election_id: str) -> None:
        self._require_admin(admin)
        election = self.elections.get(election_id)
        if election is None:
            raise VotingServiceError(f"Unknown election: {election_id}")
        election.start()

    def end_election(self, admin: Admin, election_id: str) -> None:
        self._require_admin(admin)
        election = self.elections.get(election_id)
        if election is None:
            raise VotingServiceError(f"Unknown election: {election_id}")
        election.end()

    # ---------------- Module 3: Candidate Management ----------------
    def add_candidate(self, admin: Admin, candidate_id: str, name: str, party: str,
                       election_id: str, photo: Optional[str] = None) -> Candidate:
        self._require_admin(admin)
        if election_id not in self.elections:
            raise VotingServiceError(f"Unknown election: {election_id}")
        if candidate_id in self.candidates:
            raise VotingServiceError(f"Candidate ID '{candidate_id}' is already registered.")
        candidate = Candidate(candidate_id=candidate_id, name=name, party=party,
                               election_id=election_id, photo=photo)
        self.candidates[candidate_id] = candidate
        self.elections[election_id].candidate_ids.append(candidate_id)
        return candidate

    # ---------------- Modules 5-7: Vote Casting / Duplicate Prevention / Blockchain Storage ----------------
    def cast_vote(self, voter: Voter, election_id: str, candidate_id: str,
                  auto_mine: bool = True) -> VoteReceipt:
        """Full vote-casting flow:
        Login (assumed done) -> choose election -> choose candidate ->
        confirm vote -> create vote transaction -> [duplicate check] ->
        add to pending -> mine block -> save blockchain.
        """
        self._require_voter(voter)

        election = self.elections.get(election_id)
        if election is None:
            raise VotingServiceError(f"Unknown election: {election_id}")
        if not election.is_active():
            raise VotingServiceError(f"Election '{election_id}' is not active.")

        candidate = self.candidates.get(candidate_id)
        if candidate is None or candidate.election_id != election_id:
            raise VotingServiceError(f"Candidate '{candidate_id}' is not standing in election '{election_id}'.")

        # ---- Module 6: Duplicate Vote Prevention ----
        if voter.has_voted_in(election_id):
            raise VotingServiceError(
                f"Voter '{voter.user_id}' has already voted in election '{election_id}'. Vote rejected.")

        self._vote_counter += 1
        vote_id = f"vote-{self._vote_counter}"
        vote_transaction = {
            "vote_id": vote_id,
            "voter_id": voter.user_id,
            "candidate_id": candidate_id,
            "election_id": election_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # ---- Module 7: Blockchain Storage ----
        self.blockchain.add_vote_to_pending(vote_transaction)
        voter.mark_voted(election_id)  # one person, one vote enforcement

        block = self.blockchain.mine_block() if auto_mine else None

        return VoteReceipt(
            vote_id=vote_id, voter_id=voter.user_id, candidate_id=candidate_id,
            election_id=election_id,
            block_index=block.index if block else -1,
            block_hash=block.hash if block else "",
        )

    # ---------------- Module 8: Vote Counting / Result Publication ----------------
    def publish_results(self, election_id: str) -> Dict[str, int]:
        """Traverses the blockchain from genesis and tallies votes for
        candidates standing in `election_id` only.
        """
        full_tally = self.blockchain.count_votes()
        election = self.elections.get(election_id)
        if election is None:
            raise VotingServiceError(f"Unknown election: {election_id}")
        return {cid: full_tally.get(cid, 0) for cid in election.candidate_ids}

    def verify_integrity(self):
        """Hash-verify the whole chain (Phase 3 workflow step 'Hash
        Verified'). Returns the same ValidationResult as
        Blockchain.is_chain_valid().
        """
        return self.blockchain.is_chain_valid()
