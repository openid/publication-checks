"""
End-to-end tests for ``publish.sh``.

Each test builds an HTML fixture, creates a temporary git repository with
the expected directory layout (including a ``to-publish/`` directory),
runs ``publish.sh`` via bash, and asserts on the exit code and the files
created inside ``to-publish/``.

These tests make **real** network calls because ``publish.sh`` fetches
``spec-list.csv`` from openid.net on every invocation.  They are marked
with ``pytest.mark.e2e`` so they can be selected or deselected easily.
"""

from __future__ import annotations

import datetime
import os
import subprocess
import sys

import pytest

# Ensure the tests directory is on sys.path so we can import siblings.
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

from conftest import _build_spec_html  # noqa: E402
from e2e_helpers import create_test_repo, run_shell_script  # noqa: E402

pytestmark = pytest.mark.e2e


def _network_available() -> bool:
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


_SKIP_NO_NETWORK = pytest.mark.skipif(
    not _network_available(),
    reason="openid.net is unreachable – network required for publish.sh e2e tests",
)


def _today_str() -> str:
    return datetime.date.today().isoformat()


_DEFAULT_CSV = (
    "Filename,Date,Size\n"
    "openid-connect-core-1_0.html,2024-01-15,123K\n"
    "openid-connect-core-1_0-final.html,2024-01-15,123K\n"
)


def _setup_publish_dir(repo_path):
    """Create the ``to-publish/`` directory that ``publish.sh`` copies into."""
    to_publish = repo_path / "to-publish"
    to_publish.mkdir(exist_ok=True)
    return to_publish


# ===================================================================
# Tests
# ===================================================================


@_SKIP_NO_NETWORK
def test_draft_publish(tmp_path):
    """Draft HTML + .md should produce versioned + unversioned .html and .md."""
    today = _today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Draft 01",
        state_suffix="draft",
        date=today,
        year=today[:4],
    )
    spec_files = {
        "connect/openid-connect-test-1_0-01.html": html,
        "connect/openid-connect-test-1_0-01.md": "# Test spec\n",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_DEFAULT_CSV,
    )
    to_publish = _setup_publish_dir(repo_path)

    result = run_shell_script("publish.sh", repo_path, scripts_path)

    assert result.returncode == 0, (
        f"Expected exit 0 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "CONGRATULATIONS" in result.stdout

    # publish.sh for DRAFT: cp to versioned, mv to unversioned
    # After cp + mv the versioned copy is in to-publish but the original is
    # moved, so we get: unversioned .html (via mv) and versioned .html (via cp)
    published = {p.name for p in to_publish.iterdir()}
    # Versioned html was copied (cp), then original was moved (mv) to unversioned
    assert "openid-connect-test-1_0.html" in published, (
        f"Unversioned HTML missing. Got: {published}"
    )
    # .md copies: versioned copy (cp), then moved to unversioned (mv)
    assert "openid-connect-test-1_0.md" in published, (
        f"Unversioned MD missing. Got: {published}"
    )


@_SKIP_NO_NETWORK
def test_draft_with_zip(tmp_path):
    """Draft HTML + .md + .zip should also produce .zip copies."""
    today = _today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Draft 01",
        state_suffix="draft",
        date=today,
        year=today[:4],
    )
    spec_files = {
        "connect/openid-connect-test-1_0-01.html": html,
        "connect/openid-connect-test-1_0-01.md": "# Test spec\n",
        "connect/openid-connect-test-1_0-01.zip": "FAKE-ZIP-DATA",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_DEFAULT_CSV,
    )
    to_publish = _setup_publish_dir(repo_path)

    result = run_shell_script("publish.sh", repo_path, scripts_path)

    assert result.returncode == 0, (
        f"Expected exit 0 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )

    published = {p.name for p in to_publish.iterdir()}
    assert "openid-connect-test-1_0.html" in published
    assert "openid-connect-test-1_0.md" in published
    assert "openid-connect-test-1_0.zip" in published, (
        f"Unversioned ZIP missing. Got: {published}"
    )


@_SKIP_NO_NETWORK
def test_final_publish(tmp_path):
    """Final HTML + .md should produce versioned, unversioned, and -final copies."""
    today = _today_str()
    html = _build_spec_html(
        title="Final: OpenID Connect Test 1.0",
        state_suffix="final",
        date=today,
        year=today[:4],
        include_history=False,
    )
    spec_files = {
        "connect/openid-connect-test-1_0-final.html": html,
        "connect/openid-connect-test-1_0-final.md": "# Test spec\n",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_DEFAULT_CSV,
    )
    to_publish = _setup_publish_dir(repo_path)

    result = run_shell_script("publish.sh", repo_path, scripts_path)

    assert result.returncode == 0, (
        f"Expected exit 0 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "CONGRATULATIONS" in result.stdout

    published = {p.name for p in to_publish.iterdir()}
    # FINAL produces: versioned (cp), unversioned (cp), -final (mv)
    assert "openid-connect-test-1_0-final.html" in published, (
        f"-final HTML missing. Got: {published}"
    )
    assert "openid-connect-test-1_0.html" in published, (
        f"Unversioned HTML missing. Got: {published}"
    )
    assert "openid-connect-test-1_0-final.md" in published, (
        f"-final MD missing. Got: {published}"
    )
    assert "openid-connect-test-1_0.md" in published, (
        f"Unversioned MD missing. Got: {published}"
    )


@_SKIP_NO_NETWORK
def test_unknown_state_fails(tmp_path):
    """An unrecognisable title should cause the script to exit 1."""
    today = _today_str()
    # Build HTML with a title that doesn't match DRAFT/FINAL/ERRATA/IMPLEMENTORS
    html = _build_spec_html(
        title="Some Random Document With No State Marker",
        state_suffix="unknown",
        date=today,
        year=today[:4],
        include_history=False,
    )
    spec_files = {
        "connect/openid-connect-test-1_0-01.html": html,
        "connect/openid-connect-test-1_0-01.md": "# Test\n",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_DEFAULT_CSV,
    )
    _setup_publish_dir(repo_path)

    result = run_shell_script("publish.sh", repo_path, scripts_path)

    assert result.returncode == 1, (
        f"Expected exit 1 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


@_SKIP_NO_NETWORK
def test_missing_source_fails(tmp_path):
    """HTML only (no .md or .xml) should fail with 'requires corresponding source'."""
    today = _today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Draft 01",
        state_suffix="draft",
        date=today,
        year=today[:4],
    )
    spec_files = {
        "connect/openid-connect-test-1_0-01.html": html,
        # No .md or .xml
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_DEFAULT_CSV,
    )
    _setup_publish_dir(repo_path)

    result = run_shell_script("publish.sh", repo_path, scripts_path)

    assert result.returncode == 1, (
        f"Expected exit 1 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "requires corresponding source" in result.stdout
