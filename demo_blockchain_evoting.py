#!/usr/bin/env python3
"""
demo_blockchain_evoting.py

Runs the three demonstration phases requested for the blockchain +
e-voting build:

    Phase 1 Demo -- Blockchain Foundation
        genesis block, mining, chain display, tamper + validation demo
    Phase 2 Demo -- E-Voting System
        register voters, create election, add candidates, cast votes,
        reject a duplicate vote, tally from the blockchain
    Phase 3 Demo -- Final Secure Voting System
        complete end-to-end workflow, printed step by step

All output is printed to stdout AND written to
results/BLOCKCHAIN_EVOTING_DEMO_LOG.md so it can be pasted directly
into the thesis as a worked example / appendix.

Usage:
    python demo_blockchain_evoting.py
"""

from __future__ import annotations
import io
import contextlib
import os

from blockchain_core.chain import Blockchain
from evoting_app.service import VotingService, VotingServiceError


def phase1_demo(out: io.StringIO):
    print("=" * 70, file=out)
    print("PHASE 1 DEMO -- Blockchain Foundation", file=out)
    print("=" * 70, file=out)

    bc = Blockchain(difficulty=3)
    print(f"\n1. Genesis block created.", file=out)
    print(f"   index={bc.chain[0].index}  hash={bc.chain[0].hash}", file=out)

    bc.add_vote_to_pending({"voter_id": "syn-voter-001", "candidate_id": "A", "election_id": "demo"})
    bc.add_vote_to_pending({"voter_id": "syn-voter-002", "candidate_id": "B", "election_id": "demo"})
    block1 = bc.mine_block()
    print(f"\n2. Mined Block 1 (2 votes sealed).", file=out)
    print(f"   index={block1.index}  nonce={block1.nonce}  hash={block1.hash}", file=out)
    print(f"   previous_hash={block1.previous_hash}", file=out)

    bc.add_vote_to_pending({"voter_id": "syn-voter-003", "candidate_id": "A", "election_id": "demo"})
    block2 = bc.mine_block()
    print(f"\n3. Mined Block 2 (1 vote sealed).", file=out)
    print(f"   index={block2.index}  nonce={block2.nonce}  hash={block2.hash}", file=out)
    print(f"   previous_hash={block2.previous_hash}", file=out)

    print(f"\n4. Full chain ({len(bc.chain)} blocks):", file=out)
    for b in bc.chain:
        print(f"   Block {b.index}: hash={b.hash}  prev={b.previous_hash[:16]}...  votes={len(b.votes)}", file=out)

    result = bc.is_chain_valid()
    print(f"\n5. Chain validation BEFORE tampering: valid={result.valid} ({result.reason})", file=out)

    print(f"\n6. Attacker directly edits Block 1's vote data (bypassing mine_block)...", file=out)
    bc.tamper_with_block(1, [{"voter_id": "syn-voter-001", "candidate_id": "B", "election_id": "demo"}])
    result_after = bc.is_chain_valid()
    print(f"   Chain validation AFTER tampering: valid={result_after.valid}", file=out)
    print(f"   Reason: {result_after.reason}", file=out)
    print(f"\n   ==> TAMPER DETECTED at block index {result_after.first_invalid_index}.", file=out)
    return bc


def phase2_demo(out: io.StringIO):
    print("\n" + "=" * 70, file=out)
    print("PHASE 2 DEMO -- E-Voting System", file=out)
    print("=" * 70, file=out)

    svc = VotingService(difficulty=3)

    admin = svc.register_admin("admin-01", "Election Admin", "admin@demo.test", "adminpass123")
    print(f"\n1. Registered admin: {admin.user_id} ({admin.name})", file=out)

    voters = []
    for i in range(1, 6):
        v = svc.register_voter(f"voter-{i:02d}", f"Synthetic Voter {i}", f"voter{i}@demo.test", f"pw{i}")
        voters.append(v)
    print(f"2. Registered {len(voters)} synthetic voters: {[v.user_id for v in voters]}", file=out)

    election = svc.create_election(admin, "demo-election", "Demo Election",
                                    "2026-08-06", "2026-08-07")
    print(f"3. Created election '{election.name}' (id={election.election_id}), status={election.status}", file=out)

    candA = svc.add_candidate(admin, "cand-A", "Candidate A", "Independent", "demo-election")
    candB = svc.add_candidate(admin, "cand-B", "Candidate B", "Independent", "demo-election")
    print(f"4. Added candidates: {candA.name}, {candB.name}", file=out)

    svc.start_election(admin, "demo-election")
    print(f"5. Election started, status={svc.elections['demo-election'].status}", file=out)

    choices = ["cand-A", "cand-A", "cand-B", "cand-A", "cand-B"]
    print(f"\n6. Casting votes:", file=out)
    for voter, choice in zip(voters, choices):
        receipt = svc.cast_vote(voter, "demo-election", choice)
        print(f"   {voter.user_id} -> {choice}  (sealed in block {receipt.block_index}, "
              f"hash={receipt.block_hash[:16]}...)", file=out)

    print(f"\n7. Attempting a DUPLICATE vote by {voters[0].user_id}...", file=out)
    try:
        svc.cast_vote(voters[0], "demo-election", "cand-B")
        print("   ERROR: duplicate vote was NOT rejected (this should not happen).", file=out)
    except VotingServiceError as e:
        print(f"   Correctly REJECTED: {e}", file=out)

    tally = svc.publish_results("demo-election")
    print(f"\n8. Vote tally (traversing the blockchain from genesis):", file=out)
    for cid, count in tally.items():
        name = svc.candidates[cid].name
        print(f"   {name}: {count} votes", file=out)

    integrity = svc.verify_integrity()
    print(f"\n9. Final chain integrity check: valid={integrity.valid}", file=out)
    return svc


def phase3_demo(out: io.StringIO):
    print("\n" + "=" * 70, file=out)
    print("PHASE 3 DEMO -- Final Secure Voting System (End-to-End Workflow)", file=out)
    print("=" * 70, file=out)

    svc = VotingService(difficulty=3)
    steps = []

    voter = svc.register_voter("voter-final", "Synthetic Voter Final", "final@demo.test", "pw-final")
    steps.append(f"1. Register voter -> {voter.user_id} registered.")

    admin = svc.register_admin("admin-final", "Admin Final", "adminf@demo.test", "pw-admin")
    steps.append(f"2. Admin login -> {admin.user_id} authenticated: "
                 f"{svc.login('admin-final', 'pw-admin').user_id == admin.user_id}")

    election = svc.create_election(admin, "final-election", "Final Workflow Election",
                                    "2026-08-06", "2026-08-07")
    steps.append(f"3. Create election -> '{election.name}' created (status={election.status}).")

    cand = svc.add_candidate(admin, "cand-X", "Candidate X", "Independent", "final-election")
    svc.add_candidate(admin, "cand-Y", "Candidate Y", "Independent", "final-election")
    steps.append(f"4. Add candidates -> Candidate X, Candidate Y added.")

    svc.start_election(admin, "final-election")
    steps.append(f"5. Start election -> status={svc.elections['final-election'].status}.")

    logged_in_voter = svc.login("voter-final", "pw-final")
    steps.append(f"6. Voter login -> {logged_in_voter.user_id} authenticated.")

    receipt = svc.cast_vote(logged_in_voter, "final-election", "cand-X")
    steps.append(f"7. Select candidate + confirm vote -> voted for {cand.name}.")
    steps.append(f"8. Vote transaction created -> vote_id={receipt.vote_id}.")
    steps.append(f"9. Vote stored in pending pool -> then sealed automatically.")
    steps.append(f"10. Block mined -> block {receipt.block_index}, hash={receipt.block_hash}.")
    steps.append(f"11. Blockchain updated -> chain length is now {len(svc.blockchain.chain)}.")

    integrity = svc.verify_integrity()
    steps.append(f"12. Hash verified -> chain valid = {integrity.valid} ({integrity.reason}).")

    tally = svc.publish_results("final-election")
    steps.append(f"13. Vote count -> {tally}.")
    steps.append(f"14. Result published -> {cand.name} leads with "
                 f"{tally['cand-X']} vote(s) to {tally['cand-Y']}.")

    for s in steps:
        print(s, file=out)
    return svc


def main():
    out = io.StringIO()
    print("# Blockchain + E-Voting System -- Demonstration Log\n", file=out)
    print("Generated by `python demo_blockchain_evoting.py`. All identities, "
          "elections and candidates below are synthetic.\n", file=out)

    phase1_demo(out)
    phase2_demo(out)
    phase3_demo(out)

    text = out.getvalue()
    print(text)

    os.makedirs("results", exist_ok=True)
    with open("results/BLOCKCHAIN_EVOTING_DEMO_LOG.md", "w") as f:
        f.write("```\n" + text + "\n```\n")
    print(f"\n[demo] Full log written to results/BLOCKCHAIN_EVOTING_DEMO_LOG.md")


if __name__ == "__main__":
    main()
