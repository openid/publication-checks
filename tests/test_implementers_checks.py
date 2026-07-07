"""Tests for Implementers Draft state checks.

Covers:
- An Implementers Draft cannot be submitted once a Final spec exists
  (post-final changes must be errata), mirroring the DRAFT check
- Implementers Draft numbering should be sequential (warning only:
  early IDs are not always present under -IDN naming on openid.net)
"""

import os
import sys

import pytest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

from conftest import _build_spec_html  # noqa: E402
from e2e_helpers import (  # noqa: E402
    create_test_repo, run_python_script, today_str,
    assert_no_unexpected_fails,
)

pytestmark = pytest.mark.e2e

_CSV_EMPTY = "Filename,Date,Size\n"

_CSV_WITH_FINAL = (
    "Filename,Date,Size\n"
    "openid-connect-test-1_0-final.html,50K,2024-01-15 12:00\n"
)

_CSV_WITH_ID1 = (
    "Filename,Date,Size\n"
    "openid-connect-test-1_0-ID1.html,48K,2023-06-01 12:00\n"
)


def _run_implementers(tmp_path, id_num=2, csv_content=_CSV_EMPTY):
    today = today_str()
    html = _build_spec_html(
        title=f"OpenID Connect Test 1.0 - Implementers Draft {id_num}",
        date=today,
        year=today[:4],
        include_history=True,
    )
    spec_files = {
        f"connect/openid-connect-test-1_0-ID{id_num}.html": html,
        f"connect/openid-connect-test-1_0-ID{id_num}.md": "# Test spec\n",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=csv_content,
    )
    return run_python_script("process.py", repo_path, scripts_path)


def test_implementers_after_final_fails(tmp_path):
    """Submitting an Implementers Draft when a Final already exists must
    fail: post-final changes are errata corrections."""
    result = _run_implementers(tmp_path, csv_content=_CSV_WITH_FINAL)

    assert result.returncode == 1, (
        f"Expected exit 1 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "Final spec already exists" in result.stdout


def test_implementers_id2_without_id1_warns(tmp_path):
    """Submitting -ID2 when -ID1 was never published should warn only
    (published specs show early IDs often missing under -IDN naming)."""
    result = _run_implementers(tmp_path, csv_content=_CSV_EMPTY)

    assert result.returncode == 0, (
        f"Expected exit 0 (warning only) but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert_no_unexpected_fails(result)
    assert "openid-connect-test-1_0-ID1.html" in result.stdout
    assert "Implementers Draft numbers should be sequential" in result.stdout


def test_implementers_id2_with_id1_published_no_warning(tmp_path):
    """Submitting -ID2 when -ID1 is already published: no warning."""
    result = _run_implementers(tmp_path, csv_content=_CSV_WITH_ID1)

    assert result.returncode == 0, (
        f"Expected exit 0 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert_no_unexpected_fails(result)
    assert "Previous Implementers Draft" not in result.stdout
