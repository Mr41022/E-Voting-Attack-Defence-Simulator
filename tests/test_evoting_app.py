import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pytest
from evoting_app.service import VotingService, VotingServiceError
from evoting_app.entities import User


def _setup_election(svc):
    admin = svc.register_admin("admin1", "Admin One", "admin1@example.test", "adminpass")
    svc.create_election(admin, "elec1", "Test Election", "2026-01-01", "2026-01-02")
    svc.add_candidate(admin, "candA", "Candidate A", "PartyA", "elec1")
    svc.add_candidate(admin, "candB", "Candidate B", "PartyB", "elec1")
    svc.start_election(admin, "elec1")
    return admin


def test_full_voting_workflow_and_results():
    svc = VotingService(difficulty=2)
    admin = _setup_election(svc)

    v1 = svc.register_voter("voter1", "Voter One", "v1@example.test", "pw1")
    v2 = svc.register_voter("voter2", "Voter Two", "v2@example.test", "pw2")

    r1 = svc.cast_vote(v1, "elec1", "candA")
    r2 = svc.cast_vote(v2, "elec1", "candB")

    assert r1.block_index >= 1
    assert svc.verify_integrity().valid is True

    results = svc.publish_results("elec1")
    assert results == {"candA": 1, "candB": 1}


def test_duplicate_vote_rejected():
    svc = VotingService(difficulty=2)
    admin = _setup_election(svc)
    voter = svc.register_voter("voter1", "Voter One", "v1@example.test", "pw1")

    svc.cast_vote(voter, "elec1", "candA")
    with pytest.raises(VotingServiceError):
        svc.cast_vote(voter, "elec1", "candB")

    results = svc.publish_results("elec1")
    assert results["candA"] == 1
    assert results["candB"] == 0


def test_vote_rejected_if_election_not_active():
    svc = VotingService(difficulty=2)
    admin = svc.register_admin("admin1", "Admin One", "a@example.test", "pw")
    svc.create_election(admin, "elec2", "Not Started", "2026-01-01", "2026-01-02")
    svc.add_candidate(admin, "candA", "Candidate A", "PartyA", "elec2")
    voter = svc.register_voter("voter1", "Voter One", "v1@example.test", "pw1")

    with pytest.raises(VotingServiceError):
        svc.cast_vote(voter, "elec2", "candA")


def test_login_rejects_wrong_password():
    svc = VotingService(difficulty=2)
    svc.register_voter("voter1", "Voter One", "v1@example.test", "correct-pw")
    with pytest.raises(VotingServiceError):
        svc.login("voter1", "wrong-pw")
    user = svc.login("voter1", "correct-pw")
    assert user.user_id == "voter1"


def test_only_admin_can_manage_election():
    svc = VotingService(difficulty=2)
    voter = svc.register_voter("voter1", "Voter One", "v1@example.test", "pw1")
    with pytest.raises(VotingServiceError):
        svc.create_election(voter, "elecX", "Bad", "2026-01-01", "2026-01-02")


def test_duplicate_user_id_cannot_reset_vote_state():
    svc = VotingService(difficulty=2)
    admin = _setup_election(svc)
    voter = svc.register_voter("voter1", "Voter One", "v1@example.test", "pw1")
    svc.cast_vote(voter, "elec1", "candA")

    with pytest.raises(VotingServiceError):
        svc.register_voter("voter1", "Replacement", "v2@example.test", "pw2")

    assert svc.publish_results("elec1")["candA"] == 1


def test_unregistered_admin_object_cannot_manage_election():
    svc = VotingService(difficulty=2)
    forged_admin = User("admin1", "Forged", "f@example.test", "hash", "admin")

    with pytest.raises(VotingServiceError):
        svc.create_election(forged_admin, "elec1", "Bad", "2026-01-01", "2026-01-02")


def test_missing_election_has_domain_error():
    svc = VotingService(difficulty=2)
    admin = svc.register_admin("admin1", "Admin One", "a@example.test", "pw")

    with pytest.raises(VotingServiceError, match="Unknown election"):
        svc.start_election(admin, "missing")


def test_election_attack_runner_reproducible():
    import sys, os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from simulation.election_attack_runner import run_election_attack_trials
    df1 = run_election_attack_trials(n_trials=5, seed=99)
    df2 = run_election_attack_trials(n_trials=5, seed=99)
    assert df1["flipped"].tolist() == df2["flipped"].tolist()
    assert df1["post_votes_A"].tolist() == df2["post_votes_A"].tolist()


def test_election_attack_chain_always_valid_under_attack():
    import sys, os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from simulation.election_attack_runner import run_election_attack_trials
    df = run_election_attack_trials(n_trials=5, seed=7)
    assert df["chain_valid_after_attack"].all()
