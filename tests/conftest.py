from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def cli():
    def run(data_dir: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "callops", "--data-dir", str(data_dir), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    return run


@pytest.fixture
def read_session():
    def read(data_dir: Path, session_id: str = "discovery-demo") -> dict:
        return json.loads((data_dir / "sessions" / f"{session_id}.json").read_text(encoding="utf-8"))

    return read
