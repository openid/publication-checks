"""Tests for #76: Check sequential draft numbers."""

import os
import sys

import pytest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)
sys.path.insert(0, os.path.join(_TESTS_DIR, ".."))

from conftest import _build_spec_html  # noqa: E402
from e2e_helpers import (  # noqa: E402
    create_test_repo, run_python_script, today_str, SKIP_NO_NETWORK,
)

pytestmark = pytest.mark.e2e


# CSV with draft 01 already published
_CSV_WITH_DRAFT_01 = (
    "Filename,Date,Size\n"
    "openid-connect-test-1_0-01.html,2024-01-15,50K\n"
)


@SKIP_NO_NETWORK
def test_draft_01_is_always_sequential(tmp_path):
    """Draft -01 (first draft) should always pass the sequential check."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Draft 01",

        date=today,
        year=today[:4],
    )
    spec_files = {
        "connect/openid-connect-test-1_0-01.html": html,
        "connect/openid-connect-test-1_0-01.md": "# Spec\n",
    }
    repo_path, scripts_path = create_test_repo(tmp_path, spec_files)
    result = run_python_script("process.py", repo_path, scripts_path)

    assert "Draft numbering is sequential" in result.stdout


@SKIP_NO_NETWORK
def test_draft_02_warns_when_01_not_on_openid_net(tmp_path):
    """Draft -02 for a test spec warns since draft -01 isn't published on openid.net."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Draft 02",

        date=today,
        year=today[:4],
    )
    html = html.replace("-01", "-02").replace("Initial draft", "Second draft")
    spec_files = {
        "connect/openid-connect-test-1_0-02.html": html,
        "connect/openid-connect-test-1_0-02.md": "# Spec\n",
    }
    repo_path, scripts_path = create_test_repo(tmp_path, spec_files)
    result = run_python_script("process.py", repo_path, scripts_path)

    # Should warn (previous draft not on openid.net) but still pass overall
    assert result.returncode == 0
    assert "not found in published specs" in result.stdout
    assert "sequential" in result.stdout


@SKIP_NO_NETWORK
def test_draft_03_warns_when_02_missing(tmp_path):
    """Draft -03 should warn when draft -02 is not in the spec list."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Draft 03",

        date=today,
        year=today[:4],
    )
    html = html.replace("-01", "-03").replace("Initial draft", "Third draft")
    spec_files = {
        # CSV only has draft 01, not 02
        "connect/openid-connect-test-1_0-03.html": html,
        "connect/openid-connect-test-1_0-03.md": "# Spec\n",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_CSV_WITH_DRAFT_01,
    )
    result = run_python_script("process.py", repo_path, scripts_path)

    # Should warn but not fail (exit 0)
    assert "WARNING" in result.stdout
    assert "not found in published specs" in result.stdout
    assert "sequential" in result.stdout
