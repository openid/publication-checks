"""E2e tests for the 'OIDC' branding check (issue #9).

'OIDC' must not appear in specs - the official name 'OpenID Connect' is
required. FAIL for FINAL/ERRATA, WARNING for drafts.
"""

import os
import sys

import pytest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

from conftest import _build_spec_html
from e2e_helpers import create_test_repo, run_python_script, today_str, assert_no_unexpected_fails

pytestmark = pytest.mark.e2e


_CSV_WITH_FINAL = (
    "Filename,Date,Size\n"
    "openid-connect-test-1_0.html,2024-01-15,50K\n"
    "openid-connect-test-1_0-final.html,2024-01-15,50K\n"
)

_CSV_EMPTY = "Filename,Date,Size\n"


def _inject_oidc(html):
    """Add a whole-word 'OIDC' occurrence to the fixture's introduction."""
    assert "This is the introduction." in html
    return html.replace("This is the introduction.", "This specification builds on OIDC.")


def test_draft_with_oidc_warns(tmp_path):
    """A draft using 'OIDC' should get a warning but still pass (exit 0)."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Draft 01",
        date=today,
        year=today[:4],
    )
    spec_files = {
        "connect/openid-connect-test-1_0-01.html": _inject_oidc(html),
        "connect/openid-connect-test-1_0-01.md": "# Test spec\n",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_CSV_EMPTY,
    )

    result = run_python_script("process.py", repo_path, scripts_path)

    assert result.returncode == 0, (
        f"Expected exit 0 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert_no_unexpected_fails(result)
    assert "WARNING: connect/openid-connect-test-1_0-01.html contains 'OIDC'" in result.stdout
    assert "OpenID Connect" in result.stdout


def test_errata_with_oidc_fails(tmp_path):
    """An errata using 'OIDC' must be rejected (exit 1)."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 incorporating errata set 1",
        date=today,
        year=today[:4],
        include_history=False,
    )
    spec_files = {
        "connect/openid-connect-test-1_0-errata1.html": _inject_oidc(html),
        "connect/openid-connect-test-1_0-errata1.md": "# Test spec\n",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_CSV_WITH_FINAL,
    )

    result = run_python_script("process.py", repo_path, scripts_path)

    assert result.returncode == 1, (
        f"Expected exit 1 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "FAIL: connect/openid-connect-test-1_0-errata1.html contains 'OIDC'" in result.stdout
    assert "official name 'OpenID Connect'" in result.stdout


def test_clean_draft_passes_oidc_check(tmp_path):
    """A spec without 'OIDC' should show the PASS line for the check."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Draft 01",
        date=today,
        year=today[:4],
    )
    spec_files = {
        "connect/openid-connect-test-1_0-01.html": html,
        "connect/openid-connect-test-1_0-01.md": "# Test spec\n",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_CSV_EMPTY,
    )

    result = run_python_script("process.py", repo_path, scripts_path)

    assert result.returncode == 0, (
        f"Expected exit 0 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert_no_unexpected_fails(result)
    assert "PASS: No 'OIDC' in connect/openid-connect-test-1_0-01.html" in result.stdout
