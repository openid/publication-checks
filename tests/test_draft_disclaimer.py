"""Tests for #75: Final/Errata specs must not contain the draft disclaimer."""

import datetime
import os
import subprocess
import sys

import pytest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)
sys.path.insert(0, os.path.join(_TESTS_DIR, ".."))

from conftest import _build_spec_html  # noqa: E402
from e2e_helpers import create_test_repo, run_python_script  # noqa: E402

pytestmark = pytest.mark.e2e

_DISCLAIMER = "This document is not an OIDF International Standard"

_CSV_WITH_FINAL = (
    "Filename,Date,Size\n"
    "openid-connect-test-1_0-final.html,2024-01-15,50K\n"
)


def _today_str():
    return datetime.date.today().isoformat()


def _network_available():
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
    reason="openid.net unreachable",
)


@_SKIP_NO_NETWORK
def test_final_with_draft_disclaimer_fails(tmp_path):
    """A FINAL spec containing the draft disclaimer should fail."""
    today = _today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0",
        state_suffix="final",
        date=today,
        year=today[:4],
        include_history=False,
        intended_status="Final",
    )
    # Inject the draft disclaimer
    html = html.replace(
        "This is the abstract",
        f"This is the abstract. {_DISCLAIMER}. It is distributed for review",
    )
    spec_files = {
        "connect/openid-connect-test-1_0-final.html": html,
        "connect/openid-connect-test-1_0-final.md": "# Spec\n",
    }
    repo_path, scripts_path = create_test_repo(tmp_path, spec_files)
    result = run_python_script("process.py", repo_path, scripts_path)

    assert result.returncode == 1
    assert "not an OIDF International Standard" in result.stdout


@_SKIP_NO_NETWORK
def test_final_without_draft_disclaimer_passes(tmp_path):
    """A FINAL spec without the draft disclaimer should pass this check."""
    today = _today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0",
        state_suffix="final",
        date=today,
        year=today[:4],
        include_history=False,
        intended_status="Final",
    )
    spec_files = {
        "connect/openid-connect-test-1_0-final.html": html,
        "connect/openid-connect-test-1_0-final.md": "# Spec\n",
    }
    repo_path, scripts_path = create_test_repo(tmp_path, spec_files)
    result = run_python_script("process.py", repo_path, scripts_path)

    assert result.returncode == 0
    assert "No draft disclaimer" in result.stdout


@_SKIP_NO_NETWORK
def test_draft_with_disclaimer_is_fine(tmp_path):
    """A DRAFT spec is allowed to have the disclaimer - no check applied."""
    today = _today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Draft 01",
        state_suffix="draft",
        date=today,
        year=today[:4],
    )
    html = html.replace(
        "This is the abstract",
        f"This is the abstract. {_DISCLAIMER}.",
    )
    spec_files = {
        "connect/openid-connect-test-1_0-01.html": html,
        "connect/openid-connect-test-1_0-01.md": "# Spec\n",
    }
    repo_path, scripts_path = create_test_repo(tmp_path, spec_files)
    result = run_python_script("process.py", repo_path, scripts_path)

    assert result.returncode == 0
