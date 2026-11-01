from datetime import date, timedelta

import pytest

from biggieflow.consent import ConsentError, ConsentRecord, ConsentRegistry


def make_record(**over):
    base = dict(
        speaker_id="spk1",
        name="Test Speaker",
        signed_on=date.today() - timedelta(days=1),
        expires_on=date.today() + timedelta(days=30),
        permitted_uses=("research",),
        revocation_contact="me@example.com",
    )
    base.update(over)
    return ConsentRecord(**base)


def enrolled_registry():
    reg = ConsentRegistry()
    reg.register(make_record())
    phrase = reg.start_liveness("spk1")
    reg.enroll("spk1", [0.1, 0.2], phrase)
    return reg


def test_no_record_blocks_everything():
    reg = ConsentRegistry()
    with pytest.raises(ConsentError):
        reg.start_liveness("ghost")
    with pytest.raises(ConsentError):
        reg.authorize_generation("ghost", "hi", "research")


def test_deceased_cannot_register():
    with pytest.raises(ConsentError):
        ConsentRegistry().register(make_record(deceased=True))


def test_bad_records_rejected():
    reg = ConsentRegistry()
    with pytest.raises(ConsentError):
        reg.register(make_record(permitted_uses=()))
    with pytest.raises(ConsentError):
        reg.register(make_record(revocation_contact=""))
    with pytest.raises(ConsentError):
        reg.register(make_record(expires_on=date.today() - timedelta(days=5)))


def test_replayed_audio_fails_liveness():
    reg = ConsentRegistry()
    reg.register(make_record())
    reg.start_liveness("spk1")
    with pytest.raises(ConsentError):
        reg.enroll("spk1", [0.1], "some old recording phrase")
    assert "spk1" not in reg.embeddings


def test_enroll_without_challenge_fails():
    reg = ConsentRegistry()
    reg.register(make_record())
    with pytest.raises(ConsentError):
        reg.enroll("spk1", [0.1], "anything")


def test_generation_happy_path_and_audit_hash_only():
    reg = enrolled_registry()
    emb = reg.authorize_generation("spk1", "secret lyric text", "research")
    assert emb == [0.1, 0.2]
    entry = reg.audit_log[-1]
    assert entry["event"] == "generate"
    assert "secret lyric text" not in reg.export_audit_log()
    assert len(entry["prompt_sha256"]) == 64


def test_unpermitted_use_denied():
    reg = enrolled_registry()
    with pytest.raises(ConsentError):
        reg.authorize_generation("spk1", "x", "advertising")


def test_revoke_deletes_embedding_and_blocks():
    reg = enrolled_registry()
    reg.revoke("spk1")
    assert "spk1" not in reg.embeddings
    with pytest.raises(ConsentError):
        reg.authorize_generation("spk1", "x", "research")
    with pytest.raises(ConsentError):
        reg.start_liveness("spk1")


def test_expired_consent_blocks():
    reg = ConsentRegistry()
    reg.register(make_record())
    phrase = reg.start_liveness("spk1")
    reg.enroll("spk1", [0.1], phrase)
    reg.records["spk1"].expires_on = date.today() - timedelta(days=1)
    with pytest.raises(ConsentError):
        reg.authorize_generation("spk1", "x", "research")
