"""Rule-based heuristic extraction with source line references."""

from __future__ import annotations

import re
from typing import Any


FACT_PATTERNS = (
    re.compile(r"\b\d[\d,]*\s+(?:technicians?|staff|field staff|locations?|service visits?)\b", re.I),
    re.compile(r"\bcurrently use [^,.!?]+", re.I),
)
OBJECTION_PATTERNS = (
    re.compile(r"\b(?:my|our|the) main concern is ([^.?!]+)", re.I),
    re.compile(r"\bI am concerned ([^.?!]+)", re.I),
    re.compile(r"\bconcern is ([^.?!]+)", re.I),
    re.compile(r"\b(?:worried that|too expensive|not ready to) ([^.?!]+)", re.I),
)
BUDGET_PATTERN = re.compile(r"\$\s?\d[\d,]*(?:\.\d{2})?")
TIMELINE_PATTERN = re.compile(
    r"\b(?:by|in|within|before|after|next)\s+(?:the\s+)?(?:next\s+)?"
    r"(?:\d+\s+)?(?:days?|weeks?|months?|quarters?|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|"
    r"January|February|March|April|May|June|July|August|September|October|November|December|"
    r"\d{4}-\d{2}-\d{2})\b",
    re.I,
)
ACTION_PATTERN = re.compile(
    r"\b(?:I['’]ll|I will)\s+(?:send|email|share|provide|schedule|call|follow up|"
    r"check|prepare|include|confirm|arrange|review|deliver)\b",
    re.I,
)
CONTACT_REQUEST_PATTERN = re.compile(
    r"\bplease\s+(?:send|email|share|provide|schedule|call|include)\b", re.I
)
CONTACT_COMMITMENT_PATTERN = re.compile(
    r"\bI can\s+(?:test|review|send|share|provide|schedule)\b", re.I
)
CONTACT_ACTION_PATTERN = re.compile(
    rf"(?:{CONTACT_REQUEST_PATTERN.pattern}|{CONTACT_COMMITMENT_PATTERN.pattern})", re.I
)
DUE_PATTERN = re.compile(
    r"\b(?:by|in|within|before|after|next)\s+(?:the\s+)?(?:next\s+)?"
    r"(?:\d+\s+)?(?:days?|weeks?|months?|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|"
    r"January|February|March|April|May|June|July|August|September|October|November|December|"
    r"\d{4}-\d{2}-\d{2})\b",
    re.I,
)


def extract_notes(turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    notes: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int]] = set()

    def add(kind: str, text: str, line: int) -> None:
        normalized = text.strip().rstrip(".,; ")
        key = (kind, normalized.casefold(), line)
        if normalized and key not in seen:
            seen.add(key)
            notes.append(
                {
                    "kind": kind,
                    "text": normalized,
                    "evidence_lines": [line],
                    "label": "HEURISTIC EXTRACTION, NOT VERIFIED",
                }
            )

    for turn in turns:
        if turn["speaker"] != "CONTACT":
            continue
        text = turn["text"]
        line = turn["line"]
        for pattern in FACT_PATTERNS:
            for match in pattern.finditer(text):
                add("fact", match.group(0), line)
        for pattern in OBJECTION_PATTERNS:
            for match in pattern.finditer(text):
                add("objection", match.group(1) if match.lastindex else match.group(0), line)
        for match in BUDGET_PATTERN.finditer(text):
            add("budget_mention", match.group(0).replace(" ", ""), line)
        for match in TIMELINE_PATTERN.finditer(text):
            add("timeline_mention", match.group(0), line)
        if CONTACT_ACTION_PATTERN.search(text):
            add("next_step_candidate", text, line)

    for turn in turns:
        if turn["speaker"] == "AGENT" and ACTION_PATTERN.search(turn["text"]):
            add("next_step_candidate", turn["text"], turn["line"])
    return notes


def extract_actions(turns: list[dict[str, Any]], session_id: str) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for turn in turns:
        speaker = turn["speaker"]
        text = turn["text"]
        if speaker == "AGENT" and ACTION_PATTERN.search(text):
            owner = "CallOps agent (suggested)"
        elif speaker == "CONTACT" and CONTACT_ACTION_PATTERN.search(text):
            owner = (
                "CallOps agent (suggested)"
                if CONTACT_REQUEST_PATTERN.search(text)
                else "Contact (suggested)"
            )
        else:
            continue
        due_match = DUE_PATTERN.search(text)
        due_hint = due_match.group(0) if due_match else "No date stated, human review needed"
        action_id = f"act-{session_id}-{len(actions) + 1:02d}"
        actions.append(
            {
                "item_id": action_id,
                "description": text,
                "owner_suggestion": owner,
                "due_hint": due_hint,
                "source_quote": text,
                "evidence_lines": [turn["line"]],
                "label": "HEURISTIC ACTION CANDIDATE, HUMAN REVIEW REQUIRED",
                "status": "DRAFT",
            }
        )
    return actions


def transcript_turn_map(turns: list[dict[str, Any]]) -> dict[int, str]:
    return {int(turn["line"]): turn["text"] for turn in turns}


def validate_actions(actions: list[dict[str, Any]], turns: list[dict[str, Any]]) -> None:
    turn_map = transcript_turn_map(turns)
    for action in actions:
        lines = action.get("evidence_lines", [])
        quote = action.get("source_quote", "")
        if not lines or not quote:
            raise ValueError(f"action {action.get('item_id', '<unknown>')} has no supporting quote")
        if not any(quote == turn_map.get(int(line)) for line in lines):
            raise ValueError(
                f"action {action.get('item_id', '<unknown>')} quote does not match its transcript evidence"
            )
