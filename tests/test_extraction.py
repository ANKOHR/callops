from __future__ import annotations

from callops.cli import _run_call
from callops.extraction import extract_actions, extract_notes
from callops.store import SessionStore


def test_discovery_notes_include_facts_objection_budget_timeline_and_line_refs(tmp_path):
    session = _run_call(SessionStore(tmp_path), "discovery")
    notes = session["notes"]
    facts = [note for note in notes if note["kind"] == "fact"]
    objections = [note for note in notes if note["kind"] == "objection"]
    budgets = [note for note in notes if note["kind"] == "budget_mention"]
    timelines = [note for note in notes if note["kind"] == "timeline_mention"]
    next_steps = [note for note in notes if note["kind"] == "next_step_candidate"]

    assert any("12 technicians" in note["text"] and note["evidence_lines"] == [2] for note in facts)
    assert any("300 service visits" in note["text"] and note["evidence_lines"] == [2] for note in facts)
    assert any("switching during our winter peak" in note["text"] and note["evidence_lines"] == [5] for note in objections)
    assert any(note["text"] == "$8,000" and note["evidence_lines"] == [7] for note in budgets)
    assert any("by November" in note["text"] and note["evidence_lines"] == [9] for note in timelines)
    assert next_steps
    assert all(note["label"].startswith("HEURISTIC") for note in notes)


def test_quiet_scenario_has_no_extracted_notes_or_actions(tmp_path):
    session = _run_call(SessionStore(tmp_path), "quiet")
    assert extract_notes(session["turns"]) == []
    assert extract_actions(session["turns"], session["session_id"]) == []


def test_notes_cli_prints_heuristic_label(tmp_path, cli):
    assert cli(tmp_path, "call", "--scenario", "discovery").returncode == 0
    result = cli(tmp_path, "notes", "discovery-demo")
    assert result.returncode == 0
    assert "HEURISTIC EXTRACTION, NOT VERIFIED" in result.stdout
    assert "L0002" in result.stdout
