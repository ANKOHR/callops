"""Deterministic rendering for scripted simulated calls."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


DEMO_SEED = 0
SCENARIO_DIR = Path(__file__).with_name("scenarios")


def available_scenarios() -> list[str]:
    return sorted(path.stem for path in SCENARIO_DIR.glob("*.json"))


def load_scenario(name: str) -> dict[str, Any]:
    if name not in available_scenarios():
        choices = ", ".join(available_scenarios())
        raise ValueError(f"unknown scenario {name!r}. Choose one of: {choices}")
    with (SCENARIO_DIR / f"{name}.json").open(encoding="utf-8") as handle:
        scenario = json.load(handle)
    if scenario.get("name") != name:
        raise ValueError(f"scenario file name does not match {name!r}")
    return scenario


def format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def render_transcript(scenario: dict[str, Any], session_id: str) -> tuple[str, list[dict[str, Any]], str]:
    start = datetime.fromisoformat(scenario["started_at"].replace("Z", "+00:00"))
    contact = scenario["contact"]
    header = [
        "SIMULATED CALL",
        "DEMO MODE. NO REAL TELEPHONY.",
        f"Scenario: {scenario['title']} ({scenario['name']})",
        f"Session: {session_id}",
        f"Contact: {contact['name']} at {contact['company']}",
        "",
    ]
    turns: list[dict[str, Any]] = []
    rendered_turns: list[str] = []
    for index, turn in enumerate(scenario["turns"], start=1):
        timestamp = format_timestamp(start + timedelta(minutes=index - 1))
        entry = {
            "line": index,
            "timestamp": timestamp,
            "speaker": turn["speaker"],
            "text": turn["text"],
        }
        turns.append(entry)
        rendered_turns.append(
            f"{index:04d} [{timestamp}] {turn['speaker']}: {turn['text']}"
        )
    transcript = "\n".join(header + rendered_turns) + "\n"
    ended_at = format_timestamp(start + timedelta(minutes=len(turns)))
    return transcript, turns, ended_at
