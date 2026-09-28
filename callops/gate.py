"""Human approval state machine for action items."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from .store import SessionStore


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def transition_action(
    store: SessionStore,
    item_id: str,
    target: str,
    by: str,
    now: Callable[[], str] = utc_now,
) -> tuple[dict[str, Any], dict[str, Any]]:
    name = by.strip()
    if not name:
        raise ValueError("a human name is required for this transition")
    if target not in {"APPROVED", "DONE"}:
        raise ValueError(f"unsupported action state {target!r}")
    session, action = store.find_action(item_id)
    current = action["status"]
    expected = "DRAFT" if target == "APPROVED" else "APPROVED"
    if current != expected:
        if target == "DONE" and current == "DRAFT":
            raise ValueError("cannot mark a DRAFT item DONE; approve it first")
        if target == "APPROVED" and current != "DRAFT":
            raise ValueError(f"cannot approve an item in {current} state")
        raise ValueError(f"cannot move an item from {current} to {target}")

    timestamp = now()
    action["status"] = target
    action["updated_at"] = timestamp
    action["updated_by"] = name
    store.save_session(session)
    event = {
        "event_id": f"approval:{item_id}:{target}",
        "type": "approval_transition",
        "session_id": session["session_id"],
        "scenario": session["scenario"],
        "item_id": item_id,
        "from": current,
        "to": target,
        "by": name,
        "timestamp": timestamp,
    }
    store.upsert_audit([event])
    return session, action
