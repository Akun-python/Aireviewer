from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run_help(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args, "--help"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def test_root_main_help_smoke() -> None:
    completed = _run_help("main.py")
    assert completed.returncode == 0
    assert "Word revision agent" in completed.stdout
    assert "--input" in completed.stdout


def test_module_main_help_smoke() -> None:
    completed = _run_help("-m", "app.main")
    assert completed.returncode == 0
    assert "Word revision agent" in completed.stdout
    assert "--intent" in completed.stdout


def test_formatting_runner_help_smoke() -> None:
    completed = _run_help("-m", "app.formatting.runner")
    assert completed.returncode == 0
    assert "Apply a formatting profile" in completed.stdout
    assert "--profile" in completed.stdout
