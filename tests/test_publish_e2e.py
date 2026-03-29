"""
End-to-end tests for ``publish.sh`` and ``publish.py``.

Each test builds an HTML fixture, creates a temporary git repository with
the expected directory layout (including a ``to-publish/`` directory),
runs the publish script via the parameterised ``run_publish`` fixture,
and asserts on the exit code and the files created inside ``to-publish/``.

These tests make **real** network calls because the publish scripts fetch
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
    create_test_repo, run_python_script, today_str, SKIP_NO_NETWORK,
    assert_no_unexpected_fails,
)

pytestmark = pytest.mark.e2e


_DEFAULT_CSV = (
    "Filename,Date,Size\n"
    "openid-connect-core-1_0.html,2024-01-15,123K\n"
    "openid-connect-core-1_0-final.html,2024-01-15,123K\n"
)


def _setup_publish_dir(repo_path):
    """Create the ``to-publish/`` directory that the publish scripts copy into."""
    to_publish = repo_path / "to-publish"
    to_publish.mkdir(exist_ok=True)
    return to_publish


# ===================================================================
# Parameterised fixture -- runs each test against shell AND python
# ===================================================================


@pytest.fixture
def run_publish():
    """Run publish.py."""
    def _run(repo_path, scripts_path):
        return run_python_script("publish.py", repo_path, scripts_path)
    return _run


# ===================================================================
# Tests
# ===================================================================


@SKIP_NO_NETWORK
def test_draft_publish(tmp_path, run_publish):
    """Draft HTML + .md should produce versioned + unversioned .html and .md."""
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
        tmp_path, spec_files, spec_list_csv_content=_DEFAULT_CSV,
    )
    to_publish = _setup_publish_dir(repo_path)

    result = run_publish(repo_path, scripts_path)

    assert result.returncode == 0, (
        f"Expected exit 0 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert_no_unexpected_fails(result)
    assert "CONGRATULATIONS" in result.stdout

    # publish for DRAFT: versioned copy + unversioned copy
    published = {p.name for p in to_publish.iterdir()}
    assert "openid-connect-test-1_0.html" in published, (
        f"Unversioned HTML missing. Got: {published}"
    )
    assert "openid-connect-test-1_0.md" in published, (
        f"Unversioned MD missing. Got: {published}"
    )


@SKIP_NO_NETWORK
def test_draft_with_zip(tmp_path, run_publish):
    """Draft HTML + .md + .zip should also produce .zip copies."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Draft 01",

        date=today,
        year=today[:4],
    )
    spec_files = {
        "connect/openid-connect-test-1_0-01.html": html,
        "connect/openid-connect-test-1_0-01.md": "# Test spec\n",
        "connect/openid-connect-test-1_0-01.zip": "FAKE-ZIP-DATA",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_DEFAULT_CSV,
    )
    to_publish = _setup_publish_dir(repo_path)

    result = run_publish(repo_path, scripts_path)

    assert result.returncode == 0, (
        f"Expected exit 0 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )

    published = {p.name for p in to_publish.iterdir()}
    assert "openid-connect-test-1_0.html" in published
    assert "openid-connect-test-1_0.md" in published
    assert "openid-connect-test-1_0.zip" in published, (
        f"Unversioned ZIP missing. Got: {published}"
    )


@SKIP_NO_NETWORK
def test_final_publish(tmp_path, run_publish):
    """Final HTML + .md should produce versioned, unversioned, and -final copies."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0",

        date=today,
        year=today[:4],
        include_history=False,
        intended_status="Final",
    )
    spec_files = {
        "connect/openid-connect-test-1_0-final.html": html,
        "connect/openid-connect-test-1_0-final.md": "# Test spec\n",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_DEFAULT_CSV,
    )
    to_publish = _setup_publish_dir(repo_path)

    result = run_publish(repo_path, scripts_path)

    assert result.returncode == 0, (
        f"Expected exit 0 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert_no_unexpected_fails(result)
    assert "CONGRATULATIONS" in result.stdout

    published = {p.name for p in to_publish.iterdir()}
    # FINAL produces: versioned (cp), unversioned (cp), -final (mv/cp)
    assert "openid-connect-test-1_0-final.html" in published, (
        f"-final HTML missing. Got: {published}"
    )
    assert "openid-connect-test-1_0.html" in published, (
        f"Unversioned HTML missing. Got: {published}"
    )
    assert "openid-connect-test-1_0-final.md" in published, (
        f"-final MD missing. Got: {published}"
    )
    assert "openid-connect-test-1_0.md" in published, (
        f"Unversioned MD missing. Got: {published}"
    )


@SKIP_NO_NETWORK
def test_unknown_state_fails(tmp_path, run_publish):
    """An unrecognisable title should cause the script to exit 1."""
    today = today_str()
    # Build HTML with a title that doesn't match DRAFT/FINAL/ERRATA/IMPLEMENTERS
    html = _build_spec_html(
        title="Some Random Document With No State Marker",

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
    _setup_publish_dir(repo_path)

    result = run_publish(repo_path, scripts_path)

    assert result.returncode == 1, (
        f"Expected exit 1 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


@SKIP_NO_NETWORK
def test_missing_source_fails(tmp_path, run_publish):
    """HTML only (no .md or .xml) should fail with 'requires corresponding source'."""
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
    _setup_publish_dir(repo_path)

    result = run_publish(repo_path, scripts_path)

    assert result.returncode == 1, (
        f"Expected exit 1 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "requires corresponding source" in result.stdout


@SKIP_NO_NETWORK
def test_errata_publish_uses_errata_suffix(tmp_path, run_publish):
    """ERRATA should create -errata# suffixed files, NOT -final.

    This verifies the fix for the publish.sh bug where ERRATA companion
    files (zip, md, xml, txt) were incorrectly copied with -final suffix.
    """
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 incorporating errata set 1",
        date=today,
        year=today[:4],
        include_history=False,
        intended_status="Final",
    )
    spec_files = {
        "connect/openid-connect-test-1_0-01.html": html,
        "connect/openid-connect-test-1_0-01.md": "# Test spec\n",
    }
    repo_path, scripts_path = create_test_repo(tmp_path, spec_files)
    to_publish = _setup_publish_dir(repo_path)

    result = run_publish(repo_path, scripts_path)

    assert result.returncode == 0, (
        f"Expected exit 0 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )

    published = {p.name for p in to_publish.iterdir()}
    # Should have an -errata# suffix (number depends on what's on openid.net)
    errata_htmls = [f for f in published if "-errata" in f and f.endswith(".html")]
    assert len(errata_htmls) >= 1, (
        f"Expected at least one -errata# HTML file. Got: {sorted(published)}"
    )
    errata_mds = [f for f in published if "-errata" in f and f.endswith(".md")]
    assert len(errata_mds) >= 1, (
        f"Expected at least one -errata# MD file. Got: {sorted(published)}"
    )
    # Should NOT have -final suffix for the errata companion files
    final_mds = [f for f in published if f.endswith("-final.md")]
    assert len(final_mds) == 0, (
        f"Bug: errata md got -final suffix instead of -errata#. Got: {sorted(published)}"
    )


@SKIP_NO_NETWORK
def test_implementers_publish(tmp_path, run_publish):
    """IMPLEMENTERS draft should produce versioned + unversioned .html and .md."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Implementers Draft 2",
        date=today,
        year=today[:4],
        include_history=False,
    )
    spec_files = {
        "connect/openid-connect-test-1_0-ID2.html": html,
        "connect/openid-connect-test-1_0-ID2.md": "# Test spec\n",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_DEFAULT_CSV,
    )
    to_publish = _setup_publish_dir(repo_path)

    result = run_publish(repo_path, scripts_path)

    assert result.returncode == 0, (
        f"Expected exit 0 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert_no_unexpected_fails(result)
    assert "CONGRATULATIONS" in result.stdout

    published = {p.name for p in to_publish.iterdir()}
    assert "openid-connect-test-1_0-ID2.html" in published, (
        f"Versioned HTML missing. Got: {published}"
    )
    assert "openid-connect-test-1_0-ID2.md" in published, (
        f"Versioned MD missing. Got: {published}"
    )
    assert "openid-connect-test-1_0.html" in published, (
        f"Unversioned HTML missing. Got: {published}"
    )
    assert "openid-connect-test-1_0.md" in published, (
        f"Unversioned MD missing. Got: {published}"
    )


@SKIP_NO_NETWORK
def test_draft_with_xml_instead_of_md(tmp_path, run_publish):
    """Draft HTML + .xml (no .md) should succeed and produce unversioned copies."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 - Draft 01",
        date=today,
        year=today[:4],
    )
    spec_files = {
        "connect/openid-connect-test-1_0-01.html": html,
        "connect/openid-connect-test-1_0-01.xml": "<spec/>",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_DEFAULT_CSV,
    )
    to_publish = _setup_publish_dir(repo_path)

    result = run_publish(repo_path, scripts_path)

    assert result.returncode == 0, (
        f"Expected exit 0 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )

    published = {p.name for p in to_publish.iterdir()}
    assert "openid-connect-test-1_0.html" in published, (
        f"Unversioned HTML missing. Got: {published}"
    )
    assert "openid-connect-test-1_0.xml" in published, (
        f"Unversioned XML missing. Got: {published}"
    )


@SKIP_NO_NETWORK
def test_final_with_zip(tmp_path, run_publish):
    """Final HTML + .md + .zip should produce -final.zip and unversioned .zip."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0",
        date=today,
        year=today[:4],
        include_history=False,
        intended_status="Final",
    )
    spec_files = {
        "connect/openid-connect-test-1_0-final.html": html,
        "connect/openid-connect-test-1_0-final.md": "# Test spec\n",
        "connect/openid-connect-test-1_0-final.zip": "FAKE-ZIP-DATA",
    }
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=_DEFAULT_CSV,
    )
    to_publish = _setup_publish_dir(repo_path)

    result = run_publish(repo_path, scripts_path)

    assert result.returncode == 0, (
        f"Expected exit 0 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )

    published = {p.name for p in to_publish.iterdir()}
    assert "openid-connect-test-1_0-final.zip" in published, (
        f"-final ZIP missing. Got: {published}"
    )
    assert "openid-connect-test-1_0.zip" in published, (
        f"Unversioned ZIP missing. Got: {published}"
    )


@SKIP_NO_NETWORK
def test_draft_versioned_copy_exists(tmp_path, run_publish):
    """Draft publish should create BOTH versioned and unversioned HTML."""
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
        tmp_path, spec_files, spec_list_csv_content=_DEFAULT_CSV,
    )
    to_publish = _setup_publish_dir(repo_path)

    result = run_publish(repo_path, scripts_path)

    assert result.returncode == 0, (
        f"Expected exit 0 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )

    published = {p.name for p in to_publish.iterdir()}
    assert "openid-connect-test-1_0-01.html" in published, (
        f"Versioned HTML missing. Got: {published}"
    )
    assert "openid-connect-test-1_0.html" in published, (
        f"Unversioned HTML missing. Got: {published}"
    )


@SKIP_NO_NETWORK
def test_errata_creates_unversioned_copy(tmp_path, run_publish):
    """ERRATA should create an unversioned copy alongside the -errata# copy."""
    today = today_str()
    html = _build_spec_html(
        title="OpenID Connect Test 1.0 incorporating errata set 1",
        date=today,
        year=today[:4],
        include_history=False,
        intended_status="Final",
    )
    spec_files = {
        "connect/openid-connect-test-1_0-01.html": html,
        "connect/openid-connect-test-1_0-01.md": "# Test spec\n",
    }
    repo_path, scripts_path = create_test_repo(tmp_path, spec_files)
    to_publish = _setup_publish_dir(repo_path)

    result = run_publish(repo_path, scripts_path)

    assert result.returncode == 0, (
        f"Expected exit 0 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )

    published = {p.name for p in to_publish.iterdir()}
    errata_htmls = [f for f in published if "-errata" in f and f.endswith(".html")]
    assert len(errata_htmls) >= 1, (
        f"Expected at least one -errata# HTML file. Got: {sorted(published)}"
    )
    assert "openid-connect-test-1_0.html" in published, (
        f"Unversioned HTML missing. Got: {sorted(published)}"
    )
