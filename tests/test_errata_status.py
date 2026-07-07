"""Tests for approved-errata header and numbering checks.

Covers:
- Approved errata must carry 'Status: Final' in the document header
  (all published errata specs do; drafts of errata are exempt)
- Errata set numbering must be sequential (failure: unlike draft
  numbers, errata sets are never skipped)
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

_CSV_WITH_FINAL = (
    "Filename,Date,Size\n"
    "openid-connect-test-1_0.html,2024-01-15,50K\n"
    "openid-connect-test-1_0-final.html,2024-01-15,50K\n"
)

_CSV_WITH_FINAL_AND_ERRATA1 = (
    _CSV_WITH_FINAL
    + "openid-connect-test-1_0-errata1.html,2025-03-01,51K\n"
)


def _errata_html(errata_set=1, intended_status=None):
    today = today_str()
    return _build_spec_html(
        title=f"OpenID Connect Test 1.0 incorporating errata set {errata_set}",
        date=today,
        year=today[:4],
        include_history=False,
        intended_status=intended_status,
    )


def _run_errata(tmp_path, html, errata_set=1, csv_content=_CSV_WITH_FINAL):
    spec_files = {
        f"connect/openid-connect-test-1_0-errata{errata_set}.html": html,
        f"connect/openid-connect-test-1_0-errata{errata_set}.md": "# Test spec\n",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=csv_content,
    )
    return run_python_script("process.py", repo_path, scripts_path)


# ===================================================================
# Status: Final header requirement for approved errata
# ===================================================================


def test_approved_errata_without_status_final_fails(tmp_path):
    """An approved errata whose header lacks 'Status: Final' must fail.

    This is the PR #191 scenario: errata documents were submitted without
    any Status entry in the header boilerplate and no check flagged it.
    """
    result = _run_errata(tmp_path, _errata_html())

    assert result.returncode == 1, (
        f"Expected exit 1 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "does not contain 'Status: Final'" in result.stdout


def test_approved_errata_with_status_final_passes(tmp_path):
    """An approved errata with 'Status: Final' in the header passes."""
    result = _run_errata(tmp_path, _errata_html(intended_status="Final"))

    assert result.returncode == 0, (
        f"Expected exit 0 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert_no_unexpected_fails(result)
    assert "CONGRATULATIONS" in result.stdout
    # errata set 1 with only a -final predecessor: no numbering complaint
    assert "Previous errata set" not in result.stdout


def test_approved_errata_plain_status_dd_accepted(tmp_path):
    """The <dd class="status">Final</dd> variant (e.g. published JARM errata)
    is accepted, not just <dd class="intended-status">."""
    html = _errata_html(intended_status="Final").replace(
        '<dd class="intended-status">Final</dd>',
        '<dd class="status">Final</dd>',
    )
    result = _run_errata(tmp_path, html)

    assert result.returncode == 0, (
        f"Expected exit 0 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert_no_unexpected_fails(result)


# ===================================================================
# Sequential errata set numbering
# ===================================================================


def test_errata_set_2_without_errata_1_fails(tmp_path):
    """Submitting -errata2 when -errata1 was never published must fail:
    unlike draft numbers, errata sets are never skipped."""
    result = _run_errata(
        tmp_path, _errata_html(errata_set=2, intended_status="Final"),
        errata_set=2, csv_content=_CSV_WITH_FINAL,
    )

    assert result.returncode == 1, (
        f"Expected exit 1 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "openid-connect-test-1_0-errata1.html" in result.stdout
    assert "Errata set numbers must be sequential" in result.stdout


def test_errata_set_2_with_errata_1_published_passes(tmp_path):
    """Submitting -errata2 when -errata1 is already published passes."""
    result = _run_errata(
        tmp_path, _errata_html(errata_set=2, intended_status="Final"),
        errata_set=2, csv_content=_CSV_WITH_FINAL_AND_ERRATA1,
    )

    assert result.returncode == 0, (
        f"Expected exit 0 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert_no_unexpected_fails(result)
    assert "Previous errata set" not in result.stdout
