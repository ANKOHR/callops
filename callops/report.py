"""Markdown and self-contained HTML CRM reports."""

from __future__ import annotations

import html
from typing import Any


def _refs(lines: list[int]) -> str:
    return ", ".join(f"L{line:04d}" for line in lines)


def render_markdown(session: dict[str, Any], audit: list[dict[str, Any]]) -> str:
    contact = session["contact"]
    lines = [
        "# SIMULATED CALL",
        "",
        "Demo mode. No real telephony.",
        "",
        f"- Session: `{session['session_id']}`",
        f"- Scenario: {session['scenario_title']} (`{session['scenario']}`)",
        f"- Contact: {contact['name']} at {contact['company']}",
        f"- Outcome: {session['outcome']}",
        f"- Started: {session['started_at']}",
        f"- State: {session['state']}",
        "",
        "## Heuristic notes",
        "",
        "These are heuristic extractions, not verified facts.",
        "",
    ]
    if session["notes"]:
        lines.extend(f"- **{note['kind']}**: {note['text']} ({_refs(note['evidence_lines'])})" for note in session["notes"])
    else:
        lines.append("- No notes extracted.")
    lines.extend(["", "## Heuristic action candidates", ""])
    if session["actions"]:
        for action in session["actions"]:
            lines.extend(
                [
                    f"### {action['item_id']} [{action['status']}]",
                    "",
                    f"- Candidate: {action['description']}",
                    f"- Owner suggestion: {action['owner_suggestion']}",
                    f"- Due hint: {action['due_hint']}",
                    f"- Supporting quote: > {action['source_quote']}",
                    f"- Transcript lines: {_refs(action['evidence_lines'])}",
                    "",
                ]
            )
    else:
        lines.append("- No action candidates extracted.")
    lines.extend(["## Approval audit trail", ""])
    session_audit = [event for event in audit if event.get("session_id") == session["session_id"]]
    transitions = [event for event in session_audit if event.get("type") == "approval_transition"]
    if transitions:
        for event in transitions:
            lines.append(
                f"- {event['timestamp']}: {event['item_id']} {event['from']} to {event['to']} by {event['by']}"
            )
    else:
        lines.append("- No approval transitions recorded.")
    lines.append("")
    return "\n".join(lines)


def render_html(session: dict[str, Any], audit: list[dict[str, Any]]) -> str:
    markdown_like = render_markdown(session, audit)
    escaped = html.escape(markdown_like)
    paragraphs = []
    for block in escaped.split("\n\n"):
        if block.startswith("# "):
            paragraphs.append(f"<h1>{block[2:]}</h1>")
        elif block.startswith("## "):
            paragraphs.append(f"<h2>{block[3:]}</h2>")
        elif block.startswith("### "):
            paragraphs.append(f"<h3>{block[4:]}</h3>")
        elif block.startswith("- "):
            items = "".join(f"<li>{line[2:]}</li>" for line in block.splitlines() if line.startswith("- "))
            paragraphs.append(f"<ul>{items}</ul>")
        elif block:
            paragraphs.append(f"<p>{block.replace(chr(10), '<br>')}</p>")
    body = "\n".join(paragraphs)
    return (
        "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<title>CallOps CRM report</title><style>"
        "body{font:16px/1.5 system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;color:#19232d}"
        "h1{background:#8b1e1e;color:white;padding:1rem;border-radius:8px}"
        "h2{margin-top:2rem;border-bottom:1px solid #ccd3d9;padding-bottom:.3rem}"
        "li{margin:.35rem 0} blockquote{margin:.2rem 0;padding-left:1rem;border-left:3px solid #777}"
        "</style></head><body>"
        + body
        + "</body></html>\n"
    )
