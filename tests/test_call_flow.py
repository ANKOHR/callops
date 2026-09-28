from __future__ import annotations


def test_discovery_call_replay_is_byte_deterministic(tmp_path, cli, read_session):
    first = cli(tmp_path, "call", "--scenario", "discovery")
    assert first.returncode == 0, first.stderr
    transcript_path = tmp_path / "sessions" / "discovery-demo.transcript.txt"
    session_path = tmp_path / "sessions" / "discovery-demo.json"
    audit_path = tmp_path / "callops-audit.jsonl"
    transcript_before = transcript_path.read_bytes()
    audit_before = audit_path.read_bytes()
    notes_before = read_session(tmp_path)["notes"]
    assert "SIMULATED CALL" in transcript_before.decode("utf-8")
    assert "0001 [2026-09-27T10:00:00Z] AGENT:" in transcript_before.decode("utf-8")
    assert "0002 [2026-09-27T10:01:00Z] CONTACT:" in transcript_before.decode("utf-8")

    second = cli(tmp_path, "call", "--scenario", "discovery")
    assert second.returncode == 0, second.stderr
    assert transcript_path.read_bytes() == transcript_before
    assert audit_path.read_bytes() == audit_before
    assert read_session(tmp_path)["notes"] == notes_before
    assert session_path.is_file()


def test_call_output_carries_simulation_notice(tmp_path, cli):
    result = cli(tmp_path, "call", "--scenario", "discovery")
    assert result.returncode == 0
    assert "SIMULATED CALL" in result.stdout
    assert "NO REAL TELEPHONY" in result.stdout
    assert "No real call was placed" in result.stdout
