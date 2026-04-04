"""
Tests using a real Implementers Draft spec (RP Metadata Choices 1.0 ID1).

Verifies that Implementers Drafts with a Document History section pass
all checks. Also tests that an ID without history gets a warning (the
OIDF rules require history for all specs except Final and Errata, but
many published IDs lack it so this is a warning not a failure).
"""
from __future__ import annotations

import os
import re
import sys

import pytest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

_REPO_ROOT = os.path.join(_TESTS_DIR, "..")
sys.path.insert(0, _REPO_ROOT)

from conftest import _build_spec_html  # noqa: E402
from e2e_helpers import (  # noqa: E402
    create_test_repo, run_python_script, today_str, assert_no_unexpected_fails,
)
import spec_validator  # noqa: E402

pytestmark = pytest.mark.e2e

FIXTURES_DIR = os.path.join(_TESTS_DIR, "fixtures")

ID_FILENAME = "openid-connect-rp-metadata-choices-1_0-ID1.html"


@pytest.fixture(scope="module")
def id_html():
    path = os.path.join(FIXTURES_DIR, ID_FILENAME)
    with open(path, encoding="utf-8") as f:
        return f.read()


# ===================================================================
# Unit-level tests: validate checks against the real ID spec
# ===================================================================


class TestRPMetadataChoicesID1:
    """Tests for openid-connect-rp-metadata-choices-1_0-ID1.html.

    A real Implementers Draft with a Document History section.
    """

    def test_filename_state_is_implementers(self):
        result = spec_validator.filename_state(ID_FILENAME)
        assert result["state"] == "IMPLEMENTERS"

    def test_content_state_is_draft(self, id_html):
        """ID title uses 'draft NN' — content state is DRAFT."""
        result = spec_validator.content_state(id_html)
        assert result["state"] == "DRAFT"

    def test_title_matches_h1(self, id_html):
        result = spec_validator.content_title(id_html)
        assert result["match"] is True

    def test_filename_matches_content(self, id_html):
        result = spec_validator.content_filename_match(id_html, ID_FILENAME)
        assert result["match"] is True

    def test_has_authors(self, id_html):
        result = spec_validator.content_authors(id_html)
        assert len(result["authors"]) >= 1

    def test_has_notices(self, id_html):
        result = spec_validator.content_notices(id_html)
        assert result["notices"] is True

    def test_has_license_text(self, id_html):
        result = spec_validator.content_notices(id_html)
        assert result["license_text_present"] is True

    def test_has_history(self, id_html):
        result = spec_validator.content_history(id_html)
        assert result["history_present"] is True

    def test_has_all_required_sections(self, id_html):
        result = spec_validator.content_struct(id_html)
        assert not result.get("missing_required"), (
            f"Missing sections: {result['missing_required']}"
        )


# ===================================================================
# E2E tests: process.py against Implementers Drafts
# ===================================================================


def test_implementers_draft_with_history_passes(tmp_path, id_html):
    """An Implementers Draft with a history section should pass all checks."""
    spec_files = {
        "connect/" + ID_FILENAME: id_html,
        "connect/openid-connect-rp-metadata-choices-1_0-ID1.md": "# Placeholder\n",
    }
    csv_content = "Filename,Date,Size\n"
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=csv_content,
    )

    # The fixture spec is dated 2025-04-24; fake today so the date check passes.
    result = run_python_script(
        "process.py", repo_path, scripts_path,
        env_overrides={"OVERRIDE_TODAY": "2025-04-24"},
    )

    assert_no_unexpected_fails(result)
    assert result.returncode == 0, (
        f"Expected exit 0 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "IMPLEMENTERS" in result.stdout


def test_implementers_draft_without_history_fails(tmp_path):
    """An Implementers Draft without history should fail.

    The OIDF rules require history for all specs except Final and Errata.
    """
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Draft 01",
        date=today,
        year=today[:4],
        include_history=False,
        include_notices=True,
        include_authors=True,
        include_all_sections=True,
    )
    spec_files = {
        "connect/openid-connect-test-1_0-ID1.html": html,
        "connect/openid-connect-test-1_0-ID1.md": "# Placeholder\n",
    }
    csv_content = "Filename,Date,Size\n"
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=csv_content,
    )

    result = run_python_script("process.py", repo_path, scripts_path)

    assert result.returncode == 1
    assert "IMPLEMENTERS" in result.stdout
    clean = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout)
    assert any("does not have a Document History section" in line for line in clean.splitlines())
