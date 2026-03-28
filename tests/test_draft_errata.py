"""Tests for DRAFT_ERRATA state detection and post-final draft rejection.

Covers:
- content_state() returns DRAFT_ERRATA when title has both errata and draft
- final_exists_in_csv() helper function
- E2e: process.py rejects DRAFT when final exists, accepts DRAFT_ERRATA
- PR #161 real-world scenario
"""

import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import spec_validator
from process import final_exists_in_csv

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

from conftest import _build_spec_html  # noqa: E402
from e2e_helpers import create_test_repo, run_python_script  # noqa: E402

import datetime


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


# ===================================================================
# Unit tests: content_state() DRAFT_ERRATA detection
# ===================================================================


class TestDraftErrataState:

    def test_errata_set_with_draft_number(self):
        html = (
            '<html><head><title>OpenID Example 1.0 incorporating errata set 1 - Draft 01</title></head>'
            '<body><h1 id="title">OpenID Example 1.0 incorporating errata set 1 - Draft 01</h1></body></html>'
        )
        result = spec_validator.content_state(html)
        assert result["state"] == "DRAFT_ERRATA"

    def test_errata_with_draft_different_format(self):
        html = (
            '<html><head><title>OpenID Example 1.0 errata 2 - draft 05</title></head>'
            '<body><h1 id="title">OpenID Example 1.0 errata 2 - draft 05</h1></body></html>'
        )
        result = spec_validator.content_state(html)
        assert result["state"] == "DRAFT_ERRATA"

    def test_approved_errata_is_still_errata(self):
        html = (
            '<html><head><title>OpenID Example 1.0 incorporating errata set 1</title></head>'
            '<body><h1 id="title">OpenID Example 1.0 incorporating errata set 1</h1></body></html>'
        )
        result = spec_validator.content_state(html)
        assert result["state"] == "ERRATA"

    def test_regular_draft_is_still_draft(self):
        html = (
            '<html><head><title>OpenID Example 1.0 - Draft 01</title></head>'
            '<body><h1 id="title">OpenID Example 1.0 - Draft 01</h1></body></html>'
        )
        result = spec_validator.content_state(html)
        assert result["state"] == "DRAFT"


# ===================================================================
# Unit tests: final_exists_in_csv()
# ===================================================================


class TestFinalExistsInCsv:

    def test_final_found(self, tmp_path):
        csv = tmp_path / "spec-list.csv"
        csv.write_text(
            "Filename,Date,Size\n"
            "openid-connect-example-1_0-final.html,2024-01-15,50K\n"
        )
        assert final_exists_in_csv("openid-connect-example-1_0", str(csv)) is True

    def test_final_not_found(self, tmp_path):
        csv = tmp_path / "spec-list.csv"
        csv.write_text(
            "Filename,Date,Size\n"
            "some-other-spec-1_0-final.html,2024-01-15,50K\n"
        )
        assert final_exists_in_csv("openid-connect-example-1_0", str(csv)) is False

    def test_missing_csv(self, tmp_path):
        assert final_exists_in_csv("anything", str(tmp_path / "nope.csv")) is False

    def test_only_drafts_no_final(self, tmp_path):
        csv = tmp_path / "spec-list.csv"
        csv.write_text(
            "Filename,Date,Size\n"
            "openid-connect-example-1_0-01.html,2024-01-15,50K\n"
            "openid-connect-example-1_0-ID1.html,2023-06-01,48K\n"
        )
        assert final_exists_in_csv("openid-connect-example-1_0", str(csv)) is False


# ===================================================================
# E2E tests: process.py with real network (DRAFT post-final rejection)
# ===================================================================


@_SKIP_NO_NETWORK
def test_draft_rejected_when_final_exists_e2e(tmp_path):
    """A plain DRAFT for openid-connect-4-identity-assurance-1_0 should be
    rejected because a -final already exists on openid.net."""
    today = _today_str()
    html = _build_spec_html(
        title="OpenID Connect for Identity Assurance 1.0 - Draft 18",
        state_suffix="draft",
        date=today,
        year=today[:4],
    )
    spec_files = {
        "ekyc-ida/openid-connect-4-identity-assurance-1_0-18.html": html,
        "ekyc-ida/openid-connect-4-identity-assurance-1_0-18.md": "# Spec\n",
    }
    repo_path, scripts_path = create_test_repo(tmp_path, spec_files)

    result = run_python_script("process.py", repo_path, scripts_path)

    assert result.returncode == 1, (
        f"Expected exit 1 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "final spec already exists" in result.stdout


@_SKIP_NO_NETWORK
def test_draft_errata_accepted_e2e(tmp_path):
    """A DRAFT_ERRATA for openid-connect-4-identity-assurance-1_0 should pass
    because the title correctly references errata and a final exists."""
    today = _today_str()
    html = _build_spec_html(
        title="OpenID Connect for Identity Assurance 1.0 incorporating errata set 1 - Draft 01",
        state_suffix="draft_errata",
        date=today,
        year=today[:4],
        include_history=True,
    )
    spec_files = {
        "ekyc-ida/openid-connect-4-identity-assurance-1_0-01.html": html,
        "ekyc-ida/openid-connect-4-identity-assurance-1_0-01.md": "# Spec\n",
    }
    repo_path, scripts_path = create_test_repo(tmp_path, spec_files)

    result = run_python_script("process.py", repo_path, scripts_path)

    assert result.returncode == 0, (
        f"Expected exit 0 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "DRAFT_ERRATA" in result.stdout
    assert "CONGRATULATIONS" in result.stdout


# ===================================================================
# PR #161 real-world test
# ===================================================================

_PUBLICATION_REPO = "/Users/joseph/Documents/openid/publication"
_PR_BRANCH = "origin/propose/openid-connect-4-identity-assurance-1_0-17"


@pytest.mark.skipif(
    not os.path.isdir(_PUBLICATION_REPO),
    reason="publication repo not available",
)
def test_pr161_ida_spec_is_draft_but_final_exists():
    """PR #161's IDA spec is titled 'draft 17' without errata language,
    so content_state correctly detects it as DRAFT. Since a final exists,
    the post-final check in process.py would reject it."""
    result = subprocess.run(
        ["git", "show",
         f"{_PR_BRANCH}:ekyc-ida/openid-connect-4-identity-assurance-1_0-17.html"],
        cwd=_PUBLICATION_REPO,
        capture_output=True,
    )
    if result.returncode != 0:
        pytest.skip("Could not load PR #161 file")
    content = result.stdout.decode("utf-8")

    state_result = spec_validator.content_state(content)
    assert state_result["state"] == "DRAFT", (
        "PR #161 IDA spec should be DRAFT (not DRAFT_ERRATA) - "
        "the title says 'draft 17' without any errata language"
    )
