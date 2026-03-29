"""Additional e2e tests for process.py covering remaining state/check paths."""

import os
import sys

import pytest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

from conftest import _build_spec_html
from e2e_helpers import create_test_repo, run_python_script, today_str, SKIP_NO_NETWORK, assert_no_unexpected_fails

pytestmark = pytest.mark.e2e


@pytest.fixture
def run_process():
    """Run process.py."""
    def _run(repo_path, scripts_path):
        return run_python_script("process.py", repo_path, scripts_path)
    return _run


# ---------------------------------------------------------------------------
# CSV content variants
# ---------------------------------------------------------------------------

_CSV_WITH_FINAL = (
    "Filename,Date,Size\n"
    "openid-connect-test-1_0.html,2024-01-15,50K\n"
    "openid-connect-test-1_0-final.html,2024-01-15,50K\n"
)

_CSV_NO_FINAL = "Filename,Date,Size\n"


# ===================================================================
# Tests
# ===================================================================


@SKIP_NO_NETWORK
def test_implementers_through_process(tmp_path, run_process):
    """An Implementers Draft with no history should pass all checks (exit 0)."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Implementers Draft 2",
        date=today,
        year=today[:4],
        include_history=False,
        include_notices=True,
        include_authors=True,
        include_all_sections=True,
    )
    spec_files = {
        "connect/openid-connect-test-1_0-ID2.html": html,
        "connect/openid-connect-test-1_0-ID2.md": "# Test spec\n",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_CSV_NO_FINAL,
    )

    result = run_process(repo_path, scripts_path)

    assert result.returncode == 0, (
        f"Expected exit 0 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert_no_unexpected_fails(result)
    assert "IMPLEMENTERS" in result.stdout
    assert "CONGRATULATIONS" in result.stdout


def test_errata_without_predecessor_final(tmp_path, run_process):
    """An errata spec whose predecessor final is missing from CSV should fail."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 incorporating errata set 1",
        date=today,
        year=today[:4],
        include_history=False,
        include_notices=True,
        include_authors=True,
        include_all_sections=True,
    )
    spec_files = {
        "connect/openid-connect-test-1_0-errata1.html": html,
        "connect/openid-connect-test-1_0-errata1.md": "# Test spec\n",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_CSV_NO_FINAL,
    )

    result = run_process(repo_path, scripts_path)

    assert result.returncode == 1, (
        f"Expected exit 1 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "predecessor final spec does not exist" in result.stdout


def test_errata_with_history_fails(tmp_path, run_process):
    """An approved errata spec that still has a history section should fail."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 incorporating errata set 1",
        date=today,
        year=today[:4],
        include_history=True,
        include_notices=True,
        include_authors=True,
        include_all_sections=True,
    )
    spec_files = {
        "connect/openid-connect-test-1_0-errata1.html": html,
        "connect/openid-connect-test-1_0-errata1.md": "# Test spec\n",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_CSV_WITH_FINAL,
    )

    result = run_process(repo_path, scripts_path)

    assert result.returncode == 1, (
        f"Expected exit 1 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "ERRATA state but history section exists" in result.stdout


def test_title_h1_mismatch(tmp_path, run_process):
    """When the <title> and <h1> tags disagree the script should fail."""
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
    # Patch the <h1> to differ from <title>
    html = html.replace(
        '<h1 id="title">OpenID Connect Test 1.0 - Draft 01</h1>',
        '<h1 id="title">Something Different</h1>',
    )
    spec_files = {
        "connect/openid-connect-test-1_0-01.html": html,
        "connect/openid-connect-test-1_0-01.md": "# Test spec\n",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_CSV_NO_FINAL,
    )

    result = run_process(repo_path, scripts_path)

    assert result.returncode == 1, (
        f"Expected exit 1 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "Title tag does not match H1 heading" in result.stdout


def test_content_filename_mismatch(tmp_path, run_process):
    """Filename says Draft 01 but content says Draft 02 -- should fail."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Draft 02",
        date=today,
        year=today[:4],
        include_history=True,
        include_notices=True,
        include_authors=True,
        include_all_sections=True,
    )
    spec_files = {
        # Filename ends in -01 but title says Draft 02
        "connect/openid-connect-test-1_0-01.html": html,
        "connect/openid-connect-test-1_0-01.md": "# Test spec\n",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_CSV_NO_FINAL,
    )

    result = run_process(repo_path, scripts_path)

    assert result.returncode == 1, (
        f"Expected exit 1 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "Content state or version number does not match filename" in result.stdout


def test_missing_authors(tmp_path, run_process):
    """A draft with no authors section should fail."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Draft 01",
        date=today,
        year=today[:4],
        include_history=True,
        include_notices=True,
        include_authors=False,
        include_all_sections=True,
    )
    spec_files = {
        "connect/openid-connect-test-1_0-01.html": html,
        "connect/openid-connect-test-1_0-01.md": "# Test spec\n",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_CSV_NO_FINAL,
    )

    result = run_process(repo_path, scripts_path)

    assert result.returncode == 1, (
        f"Expected exit 1 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "Problem with authors" in result.stdout


@SKIP_NO_NETWORK
def test_approved_errata_accepted(tmp_path, run_process):
    """An approved errata with no history and a predecessor final should pass."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 incorporating errata set 1",
        date=today,
        year=today[:4],
        include_history=False,
        include_notices=True,
        include_authors=True,
        include_all_sections=True,
    )
    spec_files = {
        "connect/openid-connect-test-1_0-errata1.html": html,
        "connect/openid-connect-test-1_0-errata1.md": "# Test spec\n",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_CSV_WITH_FINAL,
    )

    result = run_process(repo_path, scripts_path)

    assert result.returncode == 0, (
        f"Expected exit 0 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert_no_unexpected_fails(result)
    assert "ERRATA" in result.stdout
    assert "CONGRATULATIONS" in result.stdout


def test_unknown_state_through_process(tmp_path, run_process):
    """An HTML file with no H1 title should be flagged as UNKNOWN."""
    today = today_str()
    html = _build_spec_html(
        title="Some Random Title",
        date=today,
        year=today[:4],
        include_history=False,
        include_notices=True,
        include_authors=True,
        include_all_sections=True,
    )
    # Remove the <h1> tag so content_state() cannot detect a state,
    # which causes it to return UNKNOWN.
    html = html.replace(
        '<h1 id="title">Some Random Title</h1>',
        '',
    )
    spec_files = {
        "connect/openid-connect-test-1_0-01.html": html,
        "connect/openid-connect-test-1_0-01.md": "# Test spec\n",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_CSV_NO_FINAL,
    )

    result = run_process(repo_path, scripts_path)

    assert result.returncode == 1, (
        f"Expected exit 1 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "Problem with document titles" in result.stdout
    assert "state is UNKNOWN" in result.stdout

