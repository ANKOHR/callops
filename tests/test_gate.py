from __future__ import annotations

import json

import pytest

from callops.cli import _run_call
from callops.gate import transition_action
from callops.store import SessionStore


def test_draft_cannot_be_marked_done(tmp_path):
    store = SessionStore(tmp_path)
    session = _run_call(store, "discovery")
    item_id = session["actions"][0]["item_id"]
    with pytest.raises(ValueError, match="cannot mark a DRAFT item DONE"):
        transition_action(store, item_id, "DONE", "Alex Morgan", now=lambda: "2026-09-27T14:00:00Z")
    assert store.find_action(item_id)[1]["status"] == "DRAFT"


def test_approval_and_done_are_audited_transitions(tmp_path):
    store = SessionStore(tmp_path)
    session = _run_call(store, "discovery")
    item_id = session["actions"][0]["item_id"]
    approved, action = transition_action(
        store, item_id, "APPROVED", "Alex Morgan", now=lambda: "2026-09-27T14:01:00Z"
    )
    assert approved["session_id"] == session["session_id"]
    assert action["status"] == "APPROVED"
    audit = store.read_audit()
    approval = next(event for event in audit if event.get("event_id") == f"approval:{item_id}:APPROVED")
    assert approval["by"] == "Alex Morgan"
    assert approval["timestamp"] == "2026-09-27T14:01:00Z"
    assert approval["from"] == "DRAFT" and approval["to"] == "APPROVED"

    _, completed = transition_action(
        store, item_id, "DONE", "Alex Morgan", now=lambda: "2026-09-27T14:03:00Z"
    )
    assert completed["status"] == "DONE"
    done_event = next(event for event in store.read_audit() if event.get("event_id") == f"approval:{item_id}:DONE")
    assert done_event["from"] == "APPROVED" and done_event["to"] == "DONE"
    assert done_event["by"] == "Alex Morgan"


def test_cli_approval_gate_refuses_draft_done_and_requires_approver(tmp_path, cli):
    assert cli(tmp_path, "call", "--scenario", "discovery").returncode == 0
    item_id = "act-discovery-demo-01"
    refused = cli(tmp_path, "done", item_id, "--by", "Alex Morgan")
    assert refused.returncode == 2
    assert "cannot mark a DRAFT item DONE" in refused.stderr
    missing_name = cli(tmp_path, "approve", item_id, "--by", " ")
    assert missing_name.returncode == 2
    assert "human name is required" in missing_name.stderr
    approved = cli(tmp_path, "approve", item_id, "--by", "Alex Morgan")
    assert approved.returncode == 0
    done = cli(tmp_path, "done", item_id, "--by", "Alex Morgan")
    assert done.returncode == 0
