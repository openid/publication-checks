"""
End-to-end tests for ``process.sh``.

Each test builds an HTML fixture, creates a temporary git repository with
the expected directory layout, runs ``process.sh`` via bash, and asserts
on the exit code and stdout content.

These tests make **real** network calls because ``process.sh`` fetches
``spec-list.csv`` from openid.net on every invocation.  They are marked
with ``pytest.mark.e2e`` so they can be selected or deselected easily.
"""

from __future__ import annotations

import os
import sys

import pytest

# Ensure the tests directory is on sys.path so we can import siblings.
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

from conftest import _build_spec_html  # noqa: E402
from e2e_helpers import (  # noqa: E402
    create_test_repo, run_python_script, today_str,
    assert_no_unexpected_fails,
)

# ---------------------------------------------------------------------------
# Marker applied to every test in this module
# ---------------------------------------------------------------------------
pytestmark = pytest.mark.e2e


@pytest.fixture
def run_process():
    """Run process.py."""
    def _run(repo_path, scripts_path):
        return run_python_script("process.py", repo_path, scripts_path)
    return _run


# ---------------------------------------------------------------------------
# Default CSV content used to pre-seed spec-list.csv.
# process.sh will overwrite this if the network call succeeds, but it
# serves as documentation of expected content and is used by tests that
# only exercise code paths *after* the CSV fetch.
# ---------------------------------------------------------------------------
_DEFAULT_CSV = (
    "Filename,Date,Size\n"
    "openid-connect-core-1_0.html,2024-01-15,123K\n"
    "openid-connect-core-1_0-final.html,2024-01-15,123K\n"
    "openid-connect-core-1_0-errata1.html,2024-06-01,125K\n"
    "openid-connect-discovery-1_0-21.html,2023-11-08,45K\n"
)


# ===================================================================
# Tests
# ===================================================================



def test_valid_draft_passes(tmp_path, run_process):
    """A fully valid draft with .md source, all sections, recent date and
    history section should exit 0 and print CONGRATULATIONS."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Draft 01",

        date=today,
        year=today[:4],
        include_history=True,
        include_notices=True,
        include_authors=True,
        include_all_sections=True,
    )
    spec_files = {
        "connect/openid-connect-test-1_0-01.html": html,
        "connect/openid-connect-test-1_0-01.md": "# Test spec\n",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_DEFAULT_CSV,
    )

    result = run_process(repo_path, scripts_path)

    assert result.returncode == 0, (
        f"Expected exit 0 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert_no_unexpected_fails(result)
    assert "CONGRATULATIONS" in result.stdout



def test_no_html_files_fails(tmp_path, run_process):
    """When no HTML files have changed the script should exit 1."""
    # Commit only a markdown file – no .html
    spec_files = {
        "connect/openid-connect-test-1_0-01.md": "# Nothing\n",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_DEFAULT_CSV,
    )

    result = run_process(repo_path, scripts_path)

    assert result.returncode == 1
    assert "No HTML files have changed" in result.stdout



def test_multiple_wg_dirs_fails(tmp_path, run_process):
    """HTML files in two WG sub-directories should trigger a failure."""
    today = today_str()
    html1 = _build_spec_html(
        title="OpenID Connect Test 1.0 - Draft 01",

        date=today,
        year=today[:4],
    )
    html2 = _build_spec_html(
        title="OpenID FAPI Test 1.0 - Draft 01",

        date=today,
        year=today[:4],
    )
    spec_files = {
        "connect/openid-connect-test-1_0-01.html": html1,
        "connect/openid-connect-test-1_0-01.md": "# Test\n",
        "fapi/openid-fapi-test-1_0-01.html": html2,
        "fapi/openid-fapi-test-1_0-01.md": "# Test\n",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_DEFAULT_CSV,
    )

    result = run_process(repo_path, scripts_path)

    assert result.returncode == 1
    assert "More than one WG sub-directory" in result.stdout
    assert "connect, fapi" in result.stdout
    # Early-exit: per-file processing must not have started (issue #171)
    assert "Processing file:" not in result.stdout



def test_unversioned_filename_fails(tmp_path, run_process):
    """An unversioned HTML file (e.g. foo-1_0.html) must fail early with a
    clear error (issue #175) rather than falling through to the misleading
    'Either Markdown or XML Source is required' message."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Financial-grade API - Part 2 1.0 - Draft 11",
        date=today,
        year=today[:4],
        include_history=True,
        include_notices=True,
        include_authors=True,
        include_all_sections=True,
    )
    spec_files = {
        "fapi/openid-financial-api-part-2-1_0-11.html": html,
        "fapi/openid-financial-api-part-2-1_0-11.md": "# Test\n",
        # Mistakenly added unversioned copy:
        "fapi/openid-financial-api-part-2-1_0.html": html,
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_DEFAULT_CSV,
    )

    result = run_process(repo_path, scripts_path)

    assert result.returncode == 1
    assert "is an unversioned filename" in result.stdout
    assert "openid-financial-api-part-2-1_0.html" in result.stdout
    # Must not reach the old misleading message
    assert "Either Markdown or XML Source is required" not in result.stdout



def test_missing_source_fails(tmp_path, run_process):
    """HTML without a .md or .xml companion should fail."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Draft 01",

        date=today,
        year=today[:4],
    )
    spec_files = {
        "connect/openid-connect-test-1_0-01.html": html,
        # No .md or .xml
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_DEFAULT_CSV,
    )

    result = run_process(repo_path, scripts_path)

    assert result.returncode == 1
    assert "Markdown or XML Source is required" in result.stdout



def test_duplicate_filename_fails(tmp_path, run_process):
    """A filename that already exists in the spec list should fail."""
    today = today_str()
    # Use a filename known to exist on openid.net/specs/
    dup_name = "openid-connect-discovery-1_0-21"
    html = _build_spec_html(
        title="OpenID Connect Discovery 1.0 - Draft 21",

        date=today,
        year=today[:4],
    )
    spec_files = {
        f"connect/{dup_name}.html": html,
        f"connect/{dup_name}.md": "# Test\n",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_DEFAULT_CSV,
    )

    result = run_process(repo_path, scripts_path)

    assert result.returncode == 1
    assert "already exists" in result.stdout



def test_draft_missing_history_fails(tmp_path, run_process):
    """A draft without a Document History section should fail."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Draft 01",

        date=today,
        year=today[:4],
        include_history=False,
    )
    spec_files = {
        "connect/openid-connect-test-1_0-01.html": html,
        "connect/openid-connect-test-1_0-01.md": "# Test\n",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_DEFAULT_CSV,
    )

    result = run_process(repo_path, scripts_path)

    assert result.returncode == 1
    assert "does not have a Document History section" in result.stdout



def test_final_with_history_fails(tmp_path, run_process):
    """A final spec that still has a history section should fail."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0",

        date=today,
        year=today[:4],
        include_history=True,
        intended_status="Final",
    )
    spec_files = {
        "connect/openid-connect-test-1_0-final.html": html,
        "connect/openid-connect-test-1_0-final.md": "# Test\n",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_DEFAULT_CSV,
    )

    result = run_process(repo_path, scripts_path)

    assert result.returncode == 1
    assert "Final spec but contains a Document History section" in result.stdout



def test_stale_date_fails(tmp_path, run_process):
    """A publication date older than 10 days should fail."""
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Draft 01",

        date="2020-01-01",
        year="2020",
    )
    spec_files = {
        "connect/openid-connect-test-1_0-01.html": html,
        "connect/openid-connect-test-1_0-01.md": "# Test\n",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_DEFAULT_CSV,
    )

    result = run_process(repo_path, scripts_path)

    assert result.returncode == 1
    assert "more than 10 days ago" in result.stdout



def test_bad_notices_fails(tmp_path, run_process):
    """Missing / incorrect Notices section should fail."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Draft 01",

        date=today,
        year=today[:4],
        include_notices=False,
    )
    spec_files = {
        "connect/openid-connect-test-1_0-01.html": html,
        "connect/openid-connect-test-1_0-01.md": "# Test\n",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_DEFAULT_CSV,
    )

    result = run_process(repo_path, scripts_path)

    assert result.returncode == 1
    assert "Problem with Notices" in result.stdout



def test_missing_structure_fails(tmp_path, run_process):
    """Omitting required structural sections should fail."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Draft 01",

        date=today,
        year=today[:4],
        include_all_sections=False,
    )
    spec_files = {
        "connect/openid-connect-test-1_0-01.html": html,
        "connect/openid-connect-test-1_0-01.md": "# Test\n",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_DEFAULT_CSV,
    )

    result = run_process(repo_path, scripts_path)

    assert result.returncode == 1
    assert "Problem with structure" in result.stdout
