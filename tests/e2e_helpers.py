"""
Helper utilities for end-to-end tests that exercise the shell scripts
(process.sh, publish.sh) against temporary git repositories.

The directory layout mirrors the GitHub Actions workflow where publication-checks
is checked out as a subdirectory named ``openid-workflow`` inside the publication
repository checkout::

    tmp_path/                 # ← git repo root  (the "publication" checkout)
        connect/              # WG sub-directory with spec files
        to-publish/           # publish.sh output directory (created when needed)
        openid-workflow/      # ← the scripts directory
            process.sh
            publish.sh
            spec_validator.py
            cli-tool.py
            requirements.txt
            spec-list.csv     # pre-seeded to satisfy -check-draft calls

From ``openid-workflow/``, ``git -C ../. diff …`` correctly targets the repo root.
"""

from __future__ import annotations

import datetime
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Optional

import pytest


def today_str() -> str:
    """Return today's date as YYYY-MM-DD."""
    return datetime.date.today().isoformat()


def network_available() -> bool:
    """Return True if we can reach openid.net (quick check)."""
    try:
        result = subprocess.run(
            ["curl", "-sf", "--max-time", "5", "-o", "/dev/null",
             "https://openid.net/specs/"],
            capture_output=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


SKIP_NO_NETWORK = pytest.mark.skipif(
    not network_available(),
    reason="openid.net unreachable",
)


# Absolute path to the real publication-checks repo root.
REPO_ROOT = Path(__file__).resolve().parent.parent

# Files that must be copied into the test scripts directory.
_SCRIPT_FILES = [
    "spec_validator.py",
    "process.py",
    "publish.py",
    "requirements.txt",
]

# Optional files that are copied only if they already exist.
_OPTIONAL_SCRIPT_FILES = []


def _ensure_python_symlink(directory: Path) -> None:
    """Create a ``python`` symlink in *directory* pointing at ``python3``.

    The shell scripts call ``python cli-tool.py``.  On systems where only
    ``python3`` is on PATH this symlink ensures the command resolves.
    """
    import sys as _sys

    python_link = directory / "python"
    if not python_link.exists():
        python3 = shutil.which("python3") or _sys.executable
        python_link.symlink_to(python3)


def create_test_repo(
    tmp_path: Path,
    spec_files: Dict[str, str],
    spec_list_csv_content: Optional[str] = None,
) -> tuple[Path, Path]:
    """Set up a temporary git repo + scripts directory for e2e testing.

    Parameters
    ----------
    tmp_path:
        The pytest ``tmp_path`` fixture (becomes the git repo root).
    spec_files:
        Mapping of *relative* paths (e.g. ``"connect/spec-1_0-01.html"``)
        to file content strings.  Directories are created as needed.
    spec_list_csv_content:
        If provided, written to ``openid-workflow/spec-list.csv`` so that the
        ``-check-draft`` CLI call can work without network access.

    Returns
    -------
    tuple of (repo_path, scripts_path)
        ``repo_path``  – the git repo root (== *tmp_path*)
        ``scripts_path`` – the ``openid-workflow/`` directory inside the repo
    """
    repo_path = tmp_path
    scripts_path = repo_path / "openid-workflow"
    scripts_path.mkdir()

    # --- Copy real script files into the test scripts directory ----------
    for fname in _SCRIPT_FILES:
        src = REPO_ROOT / fname
        if src.exists():
            shutil.copy2(src, scripts_path / fname)

    for fname in _OPTIONAL_SCRIPT_FILES:
        src = REPO_ROOT / fname
        if src.exists():
            shutil.copy2(src, scripts_path / fname)

    # --- Ensure ``python`` is available in scripts_path --------------------
    # The shell scripts invoke ``python cli-tool.py`` but many systems only
    # ship ``python3``.  Create a symlink so bash can find it.
    _ensure_python_symlink(scripts_path)

    # --- Pre-seed spec-list.csv ------------------------------------------
    if spec_list_csv_content is not None:
        (scripts_path / "spec-list.csv").write_text(spec_list_csv_content)

    # --- Initialise the git repository -----------------------------------
    _git = lambda *args: subprocess.run(
        ["git"] + list(args),
        cwd=str(repo_path),
        capture_output=True,
        text=True,
        check=True,
    )

    _git("init", "-b", "main")
    _git("config", "user.email", "test@example.com")
    _git("config", "user.name", "Test User")

    # Initial commit on main (needed so origin/main ref exists)
    readme = repo_path / "README.md"
    readme.write_text("# Test publication repo\n")
    _git("add", "README.md")
    _git("commit", "-m", "Initial commit")

    # Create a local branch named ``origin/main`` that points at main.
    # This is cheaper than setting up a real remote and lets the shell
    # script's ``git diff origin/main...HEAD`` work correctly.
    _git("branch", "origin/main", "main")

    # Switch to the proposal branch and commit spec files.
    _git("checkout", "-b", "propose/test")

    for relpath, content in spec_files.items():
        full = repo_path / relpath
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content)
        _git("add", relpath)

    if spec_files:
        _git("commit", "-m", "Add spec files for testing")

    return repo_path, scripts_path


def run_shell_script(
    script_name: str,
    repo_path: Path,
    scripts_path: Path,
    *,
    timeout: int = 120,
    env_overrides: Optional[Dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    """Run a shell script from the scripts directory.

    The script is executed with ``bash`` so that it works even if the file
    lacks the executable bit.  The working directory is set to *scripts_path*
    so that relative paths in the scripts (``../$file``, ``git -C ../.``)
    resolve correctly.

    Returns the ``CompletedProcess`` instance (stdout and stderr decoded as
    UTF-8, never raises on non-zero exit).
    """
    env = os.environ.copy()
    # Prepend scripts_path so the ``python`` symlink is found first.
    env["PATH"] = str(scripts_path) + os.pathsep + env.get("PATH", "")
    if env_overrides:
        env.update(env_overrides)

    return subprocess.run(
        ["bash", str(scripts_path / script_name)],
        cwd=str(scripts_path),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


def assert_no_unexpected_fails(result):
    """Assert that a script's output contains no FAIL: lines."""
    import re
    clean = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout)
    fail_lines = [line.strip() for line in clean.splitlines() if line.strip().startswith("FAIL:")]
    assert not fail_lines, (
        f"Unexpected failures:\n" + "\n".join(f"  {f}" for f in fail_lines)
    )


def run_python_script(
    script_name: str,
    repo_path: Path,
    scripts_path: Path,
    *,
    timeout: int = 120,
    env_overrides: Optional[Dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    """Run a Python script from the scripts directory.

    Same interface as :func:`run_shell_script` but invokes via ``python3``.
    """
    import sys

    env = os.environ.copy()
    # Use pre-seeded spec-list.csv instead of fetching from network
    env["SKIP_CSV_FETCH"] = "1"
    if env_overrides:
        env.update(env_overrides)

    return subprocess.run(
        [sys.executable, str(scripts_path / script_name)],
        cwd=str(scripts_path),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
