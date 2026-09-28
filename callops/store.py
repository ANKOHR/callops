"""JSON session and JSONL audit persistence."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


SESSION_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class SessionStore:
    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self.sessions_dir = self.data_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _validate_id(self, session_id: str) -> None:
        if not SESSION_ID_PATTERN.fullmatch(session_id):
            raise ValueError("session ID may contain only lowercase letters, digits, hyphens, and underscores")

    def session_path(self, session_id: str) -> Path:
        self._validate_id(session_id)
        return self.sessions_dir / f"{session_id}.json"

    def transcript_path(self, session_id: str) -> Path:
        self._validate_id(session_id)
        return self.sessions_dir / f"{session_id}.transcript.txt"

    @property
    def audit_path(self) -> Path:
        return self.data_dir / "callops-audit.jsonl"

    def write_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_text(content, encoding="utf-8", newline="\n")
        temporary.replace(path)

    def write_json(self, path: Path, value: Any) -> None:
        self.write_text(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

    def save_session(self, session: dict[str, Any]) -> None:
        self.write_json(self.session_path(session["session_id"]), session)

    def load_session(self, session_id: str) -> dict[str, Any]:
        path = self.session_path(session_id)
        if not path.is_file():
            raise ValueError(f"session {session_id!r} was not found")
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)

    def find_action(self, item_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        for path in sorted(self.sessions_dir.glob("*.json")):
            with path.open(encoding="utf-8") as handle:
                session = json.load(handle)
            for action in session.get("actions", []):
                if action.get("item_id") == item_id:
                    return session, action
        raise ValueError(f"action item {item_id!r} was not found")

    def read_audit(self) -> list[dict[str, Any]]:
        if not self.audit_path.exists():
            return []
        events: list[dict[str, Any]] = []
        for line in self.audit_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
        return events

    def upsert_audit(self, events: list[dict[str, Any]]) -> None:
        existing = self.read_audit()
        positions = {event["event_id"]: index for index, event in enumerate(existing)}
        for event in events:
            event_id = event["event_id"]
            if event_id in positions:
                existing[positions[event_id]] = event
            else:
                positions[event_id] = len(existing)
                existing.append(event)
        if existing:
            serialized = "".join(
                json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
                for event in existing
            )
            self.write_text(self.audit_path, serialized)
