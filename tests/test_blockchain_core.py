import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from blockchain_core.chain import Blockchain
from blockchain_core.block import Block


def test_genesis_block_created_and_valid():
    bc = Blockchain(difficulty=2)
    assert len(bc.chain) == 1
    assert bc.chain[0].index == 0
    assert bc.chain[0].hash.startswith("00")
    assert bc.is_chain_valid().valid


def test_mining_produces_valid_proof_of_work():
    bc = Blockchain(difficulty=3)
    bc.add_vote_to_pending({"voter_id": "v1", "candidate_id": "A"})
    block = bc.mine_block()
    assert block.hash.startswith("000")
    assert block.hash == block.compute_hash()
    assert block.previous_hash == bc.chain[-2].hash


def test_chain_linkage_across_multiple_blocks():
    bc = Blockchain(difficulty=2)
    for i in range(3):
        bc.add_vote_to_pending({"voter_id": f"v{i}", "candidate_id": "A"})
        bc.mine_block()
    assert len(bc.chain) == 4  # genesis + 3
    for i in range(1, len(bc.chain)):
        assert bc.chain[i].previous_hash == bc.chain[i - 1].hash
    assert bc.is_chain_valid().valid


def test_tamper_detection():
    bc = Blockchain(difficulty=2)
    bc.add_vote_to_pending({"voter_id": "v1", "candidate_id": "A"})
    bc.mine_block()
    bc.add_vote_to_pending({"voter_id": "v2", "candidate_id": "A"})
    bc.mine_block()

    assert bc.is_chain_valid().valid is True
    bc.tamper_with_block(1, [{"voter_id": "v1", "candidate_id": "B"}])
    result = bc.is_chain_valid()
    assert result.valid is False
    assert result.first_invalid_index == 1


def test_vote_counting_traverses_all_blocks():
    bc = Blockchain(difficulty=2)
    bc.add_vote_to_pending({"voter_id": "v1", "candidate_id": "A"})
    bc.add_vote_to_pending({"voter_id": "v2", "candidate_id": "B"})
    bc.mine_block()
    bc.add_vote_to_pending({"voter_id": "v3", "candidate_id": "A"})
    bc.mine_block()
    tally = bc.count_votes()
    assert tally == {"A": 2, "B": 1}


def test_replace_chain_rejects_invalid_or_shorter():
    bc = Blockchain(difficulty=2)
    bc.add_vote_to_pending({"voter_id": "v1", "candidate_id": "A"})
    bc.mine_block()

    # shorter chain rejected
    other = Blockchain(difficulty=2)
    assert bc.replace_chain(other.chain) is False

    # tampered (but same-length-or-longer) chain rejected
    bc2 = Blockchain(difficulty=2)
    bc2.add_vote_to_pending({"voter_id": "vX", "candidate_id": "A"})
    bc2.mine_block()
    bc2.tamper_with_block(1, [{"voter_id": "vX", "candidate_id": "Z"}])
    assert bc.replace_chain(bc2.chain) is False


def test_add_block_rejects_bad_previous_hash():
    bc = Blockchain(difficulty=2)
    fake_block = Block.new(index=99, votes=[], previous_hash="deadbeef")
    fake_block.hash = fake_block.compute_hash()
    assert bc.add_block(fake_block) is False
