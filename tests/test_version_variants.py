"""Tests to verify that version numbers other than 1.0 are handled correctly.

All filename patterns, content state detection, and publish logic should
work with any version (1.1, 2.0, etc.), not just 1.0.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import spec_validator

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

from conftest import _build_spec_html  # noqa: E402
from e2e_helpers import (  # noqa: E402
    create_test_repo, run_python_script, today_str, SKIP_NO_NETWORK,
    assert_no_unexpected_fails,
)


# ===================================================================
# Filename state with various versions
# ===================================================================


class TestFilenameVersionVariants:

    @pytest.mark.parametrize("version,filename", [
        ("1_0", "openid-example-1_0-01.html"),
        ("1_1", "openid-example-1_1-01.html"),
        ("2_0", "openid-example-2_0-01.html"),
        ("10_3", "openid-example-10_3-05.html"),
    ])
    def test_draft_versions(self, version, filename):
        result = spec_validator.filename_state(filename)
        assert result["state"] == "DRAFT"

    @pytest.mark.parametrize("version,filename", [
        ("1_0", "openid-example-1_0-final.html"),
        ("1_1", "openid-example-1_1-final.html"),
        ("2_0", "openid-example-2_0-final.html"),
    ])
    def test_final_versions(self, version, filename):
        result = spec_validator.filename_state(filename)
        assert result["state"] == "FINAL"

    @pytest.mark.parametrize("version,filename", [
        ("1_0", "openid-example-1_0-errata1.html"),
        ("2_0", "openid-example-2_0-errata3.html"),
    ])
    def test_errata_versions(self, version, filename):
        result = spec_validator.filename_state(filename)
        assert result["state"] == "ERRATA"

    @pytest.mark.parametrize("version,filename", [
        ("1_0", "openid-example-1_0-ID1.html"),
        ("2_0", "openid-example-2_0-ID2.html"),
    ])
    def test_implementers_versions(self, version, filename):
        result = spec_validator.filename_state(filename)
        assert result["state"] == "IMPLEMENTERS"

    @pytest.mark.parametrize("version,filename", [
        ("1_0", "openid-example-1_0.html"),
        ("1_1", "openid-example-1_1.html"),
        ("2_0", "openid-example-2_0.html"),
    ])
    def test_current_versions(self, version, filename):
        result = spec_validator.filename_state(filename)
        assert result["state"] == "CURRENT"


# ===================================================================
# Content state with various versions
# ===================================================================


class TestContentStateVersionVariants:

    @pytest.mark.parametrize("version", ["1.0", "1.1", "2.0", "10.3"])
    def test_draft_version_detected(self, version):
        html = (
            f"<html><head><title>OpenID Example {version} - Draft 01</title></head>"
            f'<body><h1 id="title">OpenID Example {version} - Draft 01</h1></body></html>'
        )
        result = spec_validator.content_state(html)
        assert result["state"] == "DRAFT"

    @pytest.mark.parametrize("version", ["1.0", "1.1", "2.0"])
    def test_final_version_detected(self, version):
        html = (
            f"<html><head><title>OpenID Example {version}</title></head>"
            f'<body><h1 id="title">OpenID Example {version}</h1>'
            f'<dd class="intended-status">Final</dd></body></html>'
        )
        result = spec_validator.content_state(html)
        assert result["state"] == "FINAL"

    @pytest.mark.parametrize("version", ["1.0", "1.1", "2.0"])
    def test_errata_version_detected(self, version):
        html = (
            f"<html><head><title>OpenID Example {version} incorporating errata set 1</title></head>"
            f'<body><h1 id="title">OpenID Example {version} incorporating errata set 1</h1></body></html>'
        )
        result = spec_validator.content_state(html)
        assert result["state"] == "ERRATA"


# ===================================================================
# Content-filename match with various versions
# ===================================================================


class TestFilenameMatchVersionVariants:

    @pytest.mark.parametrize("version_file,version_title", [
        ("1_0", "1.0"),
        ("1_1", "1.1"),
        ("2_0", "2.0"),
    ])
    def test_draft_match(self, version_file, version_title):
        filename = f"openid-example-{version_file}-01.html"
        html = (
            f"<html><head><title>OpenID Example {version_title} - Draft 01</title></head>"
            f'<body><h1 id="title">OpenID Example {version_title} - Draft 01</h1></body></html>'
        )
        result = spec_validator.content_filename_match(html, filename)
        assert result["match"] is True

    @pytest.mark.parametrize("version_file,version_title", [
        ("1_0", "1.0"),
        ("2_0", "2.0"),
    ])
    def test_final_match(self, version_file, version_title):
        filename = f"openid-example-{version_file}-final.html"
        html = (
            f"<html><head><title>OpenID Example {version_title}</title></head>"
            f'<body><h1 id="title">OpenID Example {version_title}</h1>'
            f'<dd class="intended-status">Final</dd></body></html>'
        )
        result = spec_validator.content_filename_match(html, filename)
        assert result["match"] is True


# ===================================================================
# E2E: process.py with version 2.0
# ===================================================================


@SKIP_NO_NETWORK
@pytest.mark.e2e
def test_process_version_2_0(tmp_path):
    """process.py should handle version 2.0 specs correctly."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Example 2.0 - Draft 01",
        date=today,
        year=today[:4],
    )
    spec_files = {
        "connect/openid-example-2_0-01.html": html,
        "connect/openid-example-2_0-01.md": "# Spec\n",
    }
    repo_path, scripts_path = create_test_repo(tmp_path, spec_files, spec_list_csv_content="Filename,Date,Size\n")
    result = run_python_script("process.py", repo_path, scripts_path)

    assert result.returncode == 0, (
        f"Expected exit 0 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert_no_unexpected_fails(result)
    assert "CONGRATULATIONS" in result.stdout


@SKIP_NO_NETWORK
@pytest.mark.e2e
def test_process_rejects_single_digit_draft_number(tmp_path):
    """process.py should reject single-digit draft numbers (must be zero-padded)."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Example 1.0 - Draft 1",
        date=today,
        year=today[:4],
    )
    spec_files = {
        "connect/openid-example-1_0-1.html": html,
        "connect/openid-example-1_0-1.md": "# Spec\n",
    }
    repo_path, scripts_path = create_test_repo(tmp_path, spec_files, spec_list_csv_content="Filename,Date,Size\n")
    result = run_python_script("process.py", repo_path, scripts_path)

    # Single-digit filename won't match DRAFT pattern, so state detection
    # or filename match will fail
    assert result.returncode == 1, (
        f"Expected exit 1 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
