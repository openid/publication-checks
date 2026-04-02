"""Tests for IETF IPR boilerplate detection and non-canonical reference URL warnings."""

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

_CSV_WITH_FINAL = (
    "Filename,Date,Size\n"
    "openid-connect-test-1_0-final.html,2024-01-15,50K\n"
)


@SKIP_NO_NETWORK
def test_ietf_trust_text_in_final_fails(tmp_path):
    """A FINAL spec containing IETF Trust IPR boilerplate should fail."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0",
        date=today,
        year=today[:4],
        include_history=False,
        intended_status="Final",
    )
    # Inject IETF Trust IPR boilerplate
    html = html.replace(
        "This is the abstract",
        "This is the abstract. This document is subject to BCP 78 and the IETF Trust Legal Provisions.",
    )
    spec_files = {
        "connect/openid-connect-test-1_0-final.html": html,
        "connect/openid-connect-test-1_0-final.md": "# Spec\n",
    }
    repo_path, scripts_path = create_test_repo(tmp_path, spec_files, spec_list_csv_content="Filename,Date,Size\n")
    result = run_python_script("process.py", repo_path, scripts_path)

    assert result.returncode == 1
    assert "IETF Trust IPR boilerplate" in result.stdout


@SKIP_NO_NETWORK
def test_ietf_trust_text_in_draft_warns(tmp_path):
    """A DRAFT spec containing IETF Trust IPR boilerplate should warn but pass."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Draft 01",
        date=today,
        year=today[:4],
    )
    # Inject IETF Trust IPR boilerplate
    html = html.replace(
        "This is the abstract",
        "This is the abstract. This document is subject to BCP 78 and the IETF Trust Legal Provisions.",
    )
    spec_files = {
        "connect/openid-connect-test-1_0-01.html": html,
        "connect/openid-connect-test-1_0-01.md": "# Spec\n",
    }
    repo_path, scripts_path = create_test_repo(tmp_path, spec_files, spec_list_csv_content="Filename,Date,Size\n")
    result = run_python_script("process.py", repo_path, scripts_path)

    assert result.returncode == 0
    assert "WARNING" in result.stdout
    assert "IETF Trust IPR boilerplate" in result.stdout


@SKIP_NO_NETWORK
def test_no_ietf_trust_text_passes(tmp_path):
    """A spec without IETF Trust IPR boilerplate should pass this check."""
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
    repo_path, scripts_path = create_test_repo(tmp_path, spec_files, spec_list_csv_content="Filename,Date,Size\n")
    result = run_python_script("process.py", repo_path, scripts_path)

    assert result.returncode == 0
    assert "No IETF Trust IPR boilerplate" in result.stdout


@SKIP_NO_NETWORK
def test_github_io_reference_warns(tmp_path):
    """A spec with openid.github.io reference should warn."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Draft 01",
        date=today,
        year=today[:4],
    )
    # Inject a non-canonical reference URL
    html = html.replace(
        'href="https://www.rfc-editor.org/rfc/rfc2119"',
        'href="https://openid.github.io/OpenID4VCI/spec.html"',
    )
    spec_files = {
        "connect/openid-connect-test-1_0-01.html": html,
        "connect/openid-connect-test-1_0-01.md": "# Spec\n",
    }
    repo_path, scripts_path = create_test_repo(tmp_path, spec_files, spec_list_csv_content="Filename,Date,Size\n")
    result = run_python_script("process.py", repo_path, scripts_path)

    assert "openid.github.io" in result.stdout
    assert "openid.net/specs/" in result.stdout


@SKIP_NO_NETWORK
def test_bitbucket_io_reference_warns(tmp_path):
    """A spec with openid.bitbucket.io reference should warn."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Draft 01",
        date=today,
        year=today[:4],
    )
    # Inject a non-canonical bitbucket reference URL
    html = html.replace(
        'href="https://www.rfc-editor.org/rfc/rfc2119"',
        'href="https://openid.bitbucket.io/fapi/fapi-2_0-security.html"',
    )
    spec_files = {
        "connect/openid-connect-test-1_0-01.html": html,
        "connect/openid-connect-test-1_0-01.md": "# Spec\n",
    }
    repo_path, scripts_path = create_test_repo(tmp_path, spec_files, spec_list_csv_content="Filename,Date,Size\n")
    result = run_python_script("process.py", repo_path, scripts_path)

    assert "openid.bitbucket.io" in result.stdout
    assert "openid.net/specs/" in result.stdout
