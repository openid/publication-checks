"""Tests for #77: History section must reference the current draft number."""

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
)

pytestmark = pytest.mark.e2e



def test_history_references_current_draft(tmp_path):
    """Draft -01 with history entry for -01 should pass."""
    today = today_str()
    # _build_spec_html generates history with "-01" entry
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Draft 01",

        date=today,
        year=today[:4],
    )
    spec_files = {
        "connect/openid-connect-test-1_0-01.html": html,
        "connect/openid-connect-test-1_0-01.md": "# Spec\n",
    }
    repo_path, scripts_path = create_test_repo(tmp_path, spec_files, spec_list_csv_content="Filename,Date,Size\n")
    result = run_python_script("process.py", repo_path, scripts_path)

    assert result.returncode == 0, (
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "History section references draft 01" in result.stdout



def test_history_missing_current_draft(tmp_path):
    """Draft -02 with history only containing -01 should fail."""
    today = today_str()
    # _build_spec_html generates history with "-01" entry only
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Draft 02",

        date=today,
        year=today[:4],
    )
    spec_files = {
        # Filename says draft 02 but history only has -01
        "connect/openid-connect-test-1_0-02.html": html,
        "connect/openid-connect-test-1_0-02.md": "# Spec\n",
    }
    repo_path, scripts_path = create_test_repo(tmp_path, spec_files, spec_list_csv_content="Filename,Date,Size\n")
    result = run_python_script("process.py", repo_path, scripts_path)

    assert result.returncode == 1, (
        f"Expected failure but got 0.\nSTDOUT:\n{result.stdout}"
    )
    assert "does not reference current draft number 02" in result.stdout
