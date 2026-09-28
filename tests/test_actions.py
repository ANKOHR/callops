from __future__ import annotations

from callops.cli import _run_call
from callops.extraction import validate_actions
from callops.store import SessionStore


def test_every_action_has_owner_and_verbatim_quote_with_resolvable_lines(tmp_path):
    session = _run_call(SessionStore(tmp_path), "discovery")
    turn_map = {turn["line"]: turn["text"] for turn in session["turns"]}
    assert session["actions"]
    validate_actions(session["actions"], session["turns"])
    for action in session["actions"]:
        assert action["owner_suggestion"]
        assert action["source_quote"]
        assert action["evidence_lines"]
        assert any(action["source_quote"] == turn_map[line] for line in action["evidence_lines"])
        assert action["status"] == "DRAFT"


def test_actions_cli_labels_heuristic_candidates_and_shows_quote(tmp_path, cli):
    assert cli(tmp_path, "call", "--scenario", "discovery").returncode == 0
    result = cli(tmp_path, "actions", "discovery-demo")
    assert result.returncode == 0
    assert "HEURISTIC ACTION CANDIDATES" in result.stdout
    assert "Source quote (L0010)" in result.stdout
