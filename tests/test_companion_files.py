"""Tests for #166: Check that companion files match previous version."""

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


@SKIP_NO_NETWORK
def test_pr161_missing_zip_warned(tmp_path):
    """PR #161 submits draft 17 without .zip, but draft 16 had one on openid.net.
    The check should warn about the missing .zip."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect for Identity Assurance 1.0 - Draft 17",

        date=today,
        year=today[:4],
    )
    # Draft 17 with .md and .xml but no .zip
    # Draft 16 on openid.net has .html, .md, .xml, .zip
    spec_files = {
        "ekyc-ida/openid-connect-4-identity-assurance-1_0-17.html": html,
        "ekyc-ida/openid-connect-4-identity-assurance-1_0-17.md": "# Spec\n",
        "ekyc-ida/openid-connect-4-identity-assurance-1_0-17.xml": "<xml/>\n",
    }
    repo_path, scripts_path = create_test_repo(tmp_path, spec_files)
    result = run_python_script("process.py", repo_path, scripts_path)

    # Should warn about missing .zip since draft 16 had one
    assert "Previous version" in result.stdout
    assert ".zip" in result.stdout


@SKIP_NO_NETWORK
def test_md_with_includes_but_no_zip_fails(tmp_path):
    """If .md references external files but no .zip is provided, should fail."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Draft 01",

        date=today,
        year=today[:4],
    )
    md_with_includes = "# Spec\n\n<{{examples/response.json}}>\n"
    spec_files = {
        "connect/openid-connect-test-1_0-01.html": html,
        "connect/openid-connect-test-1_0-01.md": md_with_includes,
        # No .zip
    }
    repo_path, scripts_path = create_test_repo(tmp_path, spec_files)
    result = run_python_script("process.py", repo_path, scripts_path)

    assert result.returncode == 1
    assert "references external files" in result.stdout
    assert ".zip" in result.stdout


@SKIP_NO_NETWORK
def test_md_without_includes_no_zip_warns(tmp_path):
    """If .md has no includes and no .zip, just warn (not fail)."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Draft 01",

        date=today,
        year=today[:4],
    )
    spec_files = {
        "connect/openid-connect-test-1_0-01.html": html,
        "connect/openid-connect-test-1_0-01.md": "# Simple spec\n\nNo includes here.\n",
    }
    repo_path, scripts_path = create_test_repo(tmp_path, spec_files)
    result = run_python_script("process.py", repo_path, scripts_path)

    assert result.returncode == 0
    assert "WARNING" in result.stdout
    assert ".zip not present" in result.stdout


@SKIP_NO_NETWORK
def test_draft_01_no_companion_check(tmp_path):
    """Draft -01 has no previous version, so no companion file check runs."""
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

    # Should not mention companion files for draft 01
    assert "Previous version" not in result.stdout
    assert result.returncode == 0
