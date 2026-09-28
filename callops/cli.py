"""Command line interface for deterministic simulated call operations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .engine import available_scenarios, load_scenario, render_transcript
from .extraction import extract_actions, extract_notes, validate_actions
from .gate import transition_action
from .report import render_html, render_markdown
from .store import SessionStore


SIMULATION_BANNER = "SIMULATED CALL | DEMO MODE | NO REAL TELEPHONY"


def _event(session: dict[str, Any], event_type: str, suffix: str, timestamp: str, **fields: Any) -> dict[str, Any]:
    return {
        "event_id": f"{session['session_id']}:{suffix}",
        "type": event_type,
        "session_id": session["session_id"],
        "scenario": session["scenario"],
        "timestamp": timestamp,
        **fields,
    }


def _action_audit_data(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "item_id": action["item_id"],
            "description": action["description"],
            "owner_suggestion": action["owner_suggestion"],
            "due_hint": action["due_hint"],
            "source_quote": action["source_quote"],
            "evidence_lines": action["evidence_lines"],
        }
        for action in actions
    ]


def _copy_matching_statuses(actions: list[dict[str, Any]], old_session: dict[str, Any] | None) -> None:
    if old_session is None:
        return
    old_by_id = {action["item_id"]: action for action in old_session.get("actions", [])}
    for action in actions:
        old = old_by_id.get(action["item_id"])
        if old and old.get("description") == action["description"] and old.get("source_quote") == action["source_quote"]:
            for key in ("status", "updated_at", "updated_by"):
                if key in old:
                    action[key] = old[key]


def _run_call(store: SessionStore, scenario_name: str, requested_session_id: str | None = None) -> dict[str, Any]:
    scenario = load_scenario(scenario_name)
    session_id = requested_session_id or scenario["session_id"]
    store.session_path(session_id)
    try:
        old_session = store.load_session(session_id)
    except ValueError:
        old_session = None

    transcript, turns, ended_at = render_transcript(scenario, session_id)
    notes = extract_notes(turns)
    actions = extract_actions(turns, session_id)
    validate_actions(actions, turns)
    _copy_matching_statuses(actions, old_session)
    session = {
        "session_id": session_id,
        "scenario": scenario["name"],
        "scenario_title": scenario["title"],
        "state": "wrapped",
        "started_at": scenario["started_at"],
        "ended_at": ended_at,
        "contact": scenario["contact"],
        "outcome": scenario["outcome"],
        "transcript_file": f"sessions/{session_id}.transcript.txt",
        "turns": turns,
        "notes": notes,
        "actions": actions,
    }
    store.write_text(store.transcript_path(session_id), transcript)
    store.save_session(session)
    store.upsert_audit(
        [
            _event(
                session,
                "call_completed",
                "call",
                ended_at,
                outcome=session["outcome"],
                transcript_file=session["transcript_file"],
            ),
            _event(
                session,
                "notes_extracted",
                "notes",
                ended_at,
                label="HEURISTIC EXTRACTION, NOT VERIFIED",
                notes=notes,
            ),
            _event(
                session,
                "action_items_created",
                "actions",
                ended_at,
                label="HEURISTIC ACTION CANDIDATES, HUMAN REVIEW REQUIRED",
                items=_action_audit_data(actions),
            ),
        ]
    )
    return session


def _refresh_notes(store: SessionStore, session_id: str) -> dict[str, Any]:
    session = store.load_session(session_id)
    session["notes"] = extract_notes(session["turns"])
    store.save_session(session)
    store.upsert_audit(
        [
            _event(
                session,
                "notes_extracted",
                "notes",
                session["ended_at"],
                label="HEURISTIC EXTRACTION, NOT VERIFIED",
                notes=session["notes"],
            )
        ]
    )
    return session


def _refresh_actions(store: SessionStore, session_id: str) -> dict[str, Any]:
    session = store.load_session(session_id)
    actions = extract_actions(session["turns"], session_id)
    validate_actions(actions, session["turns"])
    _copy_matching_statuses(actions, session)
    session["actions"] = actions
    store.save_session(session)
    store.upsert_audit(
        [
            _event(
                session,
                "action_items_created",
                "actions",
                session["ended_at"],
                label="HEURISTIC ACTION CANDIDATES, HUMAN REVIEW REQUIRED",
                items=_action_audit_data(actions),
            )
        ]
    )
    return session


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="callops",
        description="Run scripted calls in simulated demo mode. No real telephony is connected.",
    )
    parser.add_argument("--data-dir", default="data", help="directory for JSON records, transcripts, reports, and audit log")
    subparsers = parser.add_subparsers(dest="command", required=True)

    call_parser = subparsers.add_parser("call", help="run a deterministic simulated call scenario")
    call_parser.add_argument("--scenario", required=True, choices=available_scenarios())
    call_parser.add_argument("--session-id", help="use a separate stable session ID for this replay")

    notes_parser = subparsers.add_parser("notes", help="extract heuristic notes from a session")
    notes_parser.add_argument("session")

    actions_parser = subparsers.add_parser("actions", help="derive quoted heuristic action candidates")
    actions_parser.add_argument("session")

    approve_parser = subparsers.add_parser("approve", help="approve a DRAFT action item as a human")
    approve_parser.add_argument("item")
    approve_parser.add_argument("--by", required=True, help="name of the human approver")

    done_parser = subparsers.add_parser("done", help="mark an APPROVED action item DONE")
    done_parser.add_argument("item")
    done_parser.add_argument("--by", required=True, help="name of the human recording completion")

    report_parser = subparsers.add_parser("report", help="write a Markdown or HTML CRM report")
    report_parser.add_argument("session")
    report_parser.add_argument("--format", choices=("md", "html"), default="md")
    return parser


def _print_notes(session: dict[str, Any]) -> None:
    print("HEURISTIC EXTRACTION, NOT VERIFIED")
    if not session["notes"]:
        print("No notes extracted.")
        return
    for note in session["notes"]:
        refs = ", ".join(f"L{line:04d}" for line in note["evidence_lines"])
        print(f"- {note['kind']}: {note['text']} ({refs})")


def _print_actions(session: dict[str, Any]) -> None:
    print("HEURISTIC ACTION CANDIDATES, HUMAN REVIEW REQUIRED")
    if not session["actions"]:
        print("No action candidates extracted.")
        return
    for action in session["actions"]:
        refs = ", ".join(f"L{line:04d}" for line in action["evidence_lines"])
        print(f"- {action['item_id']} [{action['status']}] {action['description']}")
        print(f"  Owner suggestion: {action['owner_suggestion']}")
        print(f"  Due hint: {action['due_hint']}")
        print(f"  Source quote ({refs}): {action['source_quote']}")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    store = SessionStore(args.data_dir)
    try:
        if args.command == "call":
            session = _run_call(store, args.scenario, args.session_id)
            print(SIMULATION_BANNER)
            print("Transcript is a scripted demo. No real call was placed.")
            print(f"Session: {session['session_id']}")
            print(f"Transcript: {store.transcript_path(session['session_id'])}")
            print(f"Notes: {len(session['notes'])} heuristic items")
            print(f"Action candidates: {len(session['actions'])}, all start in DRAFT")
            print(store.transcript_path(session["session_id"]).read_text(encoding="utf-8"), end="")
            return 0
        if args.command == "notes":
            session = _refresh_notes(store, args.session)
            _print_notes(session)
            return 0
        if args.command == "actions":
            session = _refresh_actions(store, args.session)
            _print_actions(session)
            return 0
        if args.command == "approve":
            session, action = transition_action(store, args.item, "APPROVED", args.by)
            print(f"{action['item_id']} moved from DRAFT to APPROVED by {args.by.strip()}.")
            print("Approval transition recorded in callops-audit.jsonl.")
            return 0
        if args.command == "done":
            session, action = transition_action(store, args.item, "DONE", args.by)
            print(f"{action['item_id']} moved from APPROVED to DONE by {args.by.strip()}.")
            print("Completion transition recorded in callops-audit.jsonl.")
            return 0
        if args.command == "report":
            session = store.load_session(args.session)
            audit = store.read_audit()
            if args.format == "html":
                content = render_html(session, audit)
                path = store.sessions_dir / f"{session['session_id']}.report.html"
            else:
                content = render_markdown(session, audit)
                path = store.sessions_dir / f"{session['session_id']}.report.md"
            store.write_text(path, content)
            print(f"Report written: {path}")
            if args.format == "html":
                print(SIMULATION_BANNER)
            else:
                print(content, end="")
            return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    parser.error("unhandled command")
    return 2
