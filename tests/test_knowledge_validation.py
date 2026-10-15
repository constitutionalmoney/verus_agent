"""Regression checks for wheel integrity under optimized Python execution."""

from pathlib import Path
import subprocess
import sys

import pytest


CHECKER = Path(__file__).resolve().parents[1] / "scripts" / "check_knowledge.py"


@pytest.mark.parametrize(
    ("names", "expected", "excluded", "error"),
    [
        (set(), {"verus_agent/knowledge/INDEX.md"}, [], "Knowledge content missing"),
        ({"verus_agent/LOCAL_OPERATOR.md"}, set(), ["LOCAL_OPERATOR.md"], "Local-only file leaked"),
        ({"verus_agent/operator-approval.local.json"}, set(), ["operator-approval.local.json"], "Local-only file leaked"),
    ],
)
def test_wheel_integrity_failures_remain_errors_with_optimization(names, expected, excluded, error):
    result = subprocess.run(
        [sys.executable, "-O", "-c",
         "import runpy, sys; checker = runpy.run_path(sys.argv[1]); "
         f"checker['validate_wheel_contents']({names!r}, {expected!r}, {excluded!r})", str(CHECKER)],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert error in result.stderr
