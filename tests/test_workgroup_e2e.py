"""Tests for publication#192: the workgroup metadata must match the WG directory.

Specs have been published with bogus workgroup values ('individual', 'Final')
that rendered into the published HTML. process.py should reject values that
are not known names for the WG directory the spec was submitted under.
"""

import os
import sys

import pytest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)
sys.path.insert(0, os.path.join(_TESTS_DIR, ".."))

from conftest import _build_spec_html  # noqa: E402
from e2e_helpers import (  # noqa: E402
    create_test_repo, run_python_script, today_str,
    assert_no_unexpected_fails,
)

pytestmark = pytest.mark.e2e

_EMPTY_CSV = "Filename,Date,Size\n"


def _run_with_workgroup(tmp_path, workgroup, wg_dir="connect"):
    """Build a draft spec with the given workgroup value under wg_dir and run process.py."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Draft 01",
        date=today,
        year=today[:4],
        workgroup=workgroup,
    )
    spec_files = {
        f"{wg_dir}/openid-connect-test-1_0-01.html": html,
        f"{wg_dir}/openid-connect-test-1_0-01.md": "# Spec\n",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_EMPTY_CSV
    )
    return run_python_script("process.py", repo_path, scripts_path)


def test_individual_workgroup_fails(tmp_path):
    """'individual' is not a working group name - must be rejected (issue #192)."""
    result = _run_with_workgroup(tmp_path, "individual")

    assert result.returncode == 1
    assert "FAIL" in result.stdout
    assert "'individual'" in result.stdout
    # The failure output should list the accepted values to help the editor
    assert "OpenID Connect Working Group" in result.stdout


def test_final_as_workgroup_fails(tmp_path):
    """'Final' (document status pasted into the wrong field) must be rejected."""
    result = _run_with_workgroup(tmp_path, "Final")

    assert result.returncode == 1
    assert "FAIL" in result.stdout
    assert "'Final'" in result.stdout


def test_wrong_wg_name_fails(tmp_path):
    """A valid name for a different WG is still wrong for this directory."""
    result = _run_with_workgroup(tmp_path, "OpenID AuthZEN")

    assert result.returncode == 1
    assert "FAIL" in result.stdout
    assert "'OpenID AuthZEN'" in result.stdout


def test_matching_workgroup_passes(tmp_path):
    """A known name for the connect directory passes."""
    result = _run_with_workgroup(tmp_path, "OpenID Connect")

    assert result.returncode == 0
    assert_no_unexpected_fails(result)
    assert "PASS: Workgroup" in result.stdout


def test_workgroup_match_is_case_insensitive(tmp_path):
    """Historical values vary in casing, so matching is case-insensitive."""
    result = _run_with_workgroup(tmp_path, "OPENID CONNECT WORKING GROUP")

    assert result.returncode == 0
    assert_no_unexpected_fails(result)
    assert "PASS: Workgroup" in result.stdout


def test_missing_workgroup_warns(tmp_path):
    """No workgroup element at all is a warning, not a failure."""
    result = _run_with_workgroup(tmp_path, None)

    assert result.returncode == 0
    assert_no_unexpected_fails(result)
    assert "WARNING: No workgroup found" in result.stdout


def test_unknown_wg_dir_warns(tmp_path):
    """A WG directory with no mapping entry warns rather than failing."""
    result = _run_with_workgroup(tmp_path, "Some New WG", wg_dir="newwg")

    assert result.returncode == 0
    assert_no_unexpected_fails(result)
    assert "No known workgroup names for directory 'newwg'" in result.stdout
