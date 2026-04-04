"""
Tests using the real FAPI Security Profile 1.0 Part 1 draft 11 spec.

Uses a copy of the actual published HTML file as a test fixture.
The spec is a pandoc-generated DRAFT_ERRATA (title includes both
"Draft 11" and "incorporating errata set 1").
"""
from __future__ import annotations

import os
import re
import sys

import pytest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

_REPO_ROOT = os.path.join(_TESTS_DIR, "..")
sys.path.insert(0, _REPO_ROOT)

from e2e_helpers import create_test_repo, run_python_script  # noqa: E402
import spec_validator  # noqa: E402

pytestmark = pytest.mark.e2e

FIXTURES_DIR = os.path.join(_TESTS_DIR, "fixtures")

FILENAME = "openid-financial-api-part-1-1_0-11.html"


@pytest.fixture(scope="module")
def fapi_html():
    path = os.path.join(FIXTURES_DIR, FILENAME)
    with open(path, encoding="utf-8") as f:
        return f.read()


# ===================================================================
# Unit-level tests: validate individual checks against the real file
# ===================================================================


class TestFAPIBaselineDraftErrata:
    """Tests for openid-financial-api-part-1-1_0-11.html.

    This is a pandoc-generated DRAFT_ERRATA spec. The title is:
    "FAPI security profile 1.0 - Part 1: Baseline - Draft 11 incorporating errata set 1"

    Filename state is DRAFT (no errata indicator in the filename),
    but content state is DRAFT_ERRATA (title contains both "Draft" and "errata").
    """

    def test_filename_state_is_draft(self):
        result = spec_validator.filename_state(FILENAME)
        assert result["state"] == "DRAFT"

    def test_content_state_is_draft_errata(self, fapi_html):
        result = spec_validator.content_state(fapi_html)
        assert result["state"] == "DRAFT_ERRATA"

    def test_filename_content_state_mismatch(self, fapi_html):
        """Filename says DRAFT but content says DRAFT_ERRATA — mismatch."""
        fn_state = spec_validator.filename_state(FILENAME)
        ct_state = spec_validator.content_state(fapi_html)
        assert fn_state["state"] != ct_state["state"]

    def test_title_matches_h1(self, fapi_html):
        result = spec_validator.content_title(fapi_html)
        assert result["match"] is True

    def test_title_contains_errata_language(self, fapi_html):
        result = spec_validator.content_title(fapi_html)
        assert "incorporating errata set 1" in result["title_tag"]

    def test_content_filename_match_is_false(self, fapi_html):
        """Filename state (DRAFT) doesn't match content state (DRAFT_ERRATA)."""
        result = spec_validator.content_filename_match(fapi_html, FILENAME)
        assert result["match"] is False

    def test_authors_detected(self, fapi_html):
        """Pandoc dd.author (singular) format — authors detected."""
        result = spec_validator.content_authors(fapi_html)
        assert len(result["authors"]) >= 1
        names = [a["name"] for a in result["authors"]]
        assert "Nat Sakimura" in names

    def test_notices_detected(self, fapi_html):
        result = spec_validator.content_notices(fapi_html)
        assert result["notices"] is True

    def test_license_text_present(self, fapi_html):
        result = spec_validator.content_notices(fapi_html)
        assert result["license_text_present"] is True

    def test_copyright_year_matches(self, fapi_html):
        result = spec_validator.content_notices(fapi_html)
        assert result["copyright_year"] == 2026
        assert result["years_match"] is True

    def test_history_detected(self, fapi_html):
        """Uses 'Appendix B (Informative) Document History' — now detected."""
        result = spec_validator.content_history(fapi_html)
        assert result["history_present"] is True

    def test_introduction_present(self, fapi_html):
        result = spec_validator.content_struct(fapi_html)
        assert result["structure"]["INTRODUCTION"] is True

    def test_abstract_not_detected(self, fapi_html):
        """Pandoc uses .abstract CSS class, not a heading — not detected."""
        result = spec_validator.content_struct(fapi_html)
        assert result["structure"]["ABSTRACT"] is False

    def test_normative_references_detected(self, fapi_html):
        result = spec_validator.content_struct(fapi_html)
        assert result["structure"]["NORMATIVE_REFERENCES"] is True

    def test_security_detected(self, fapi_html):
        result = spec_validator.content_struct(fapi_html)
        assert result["structure"]["SECURITY"] is True

    def test_acknowledgements_detected(self, fapi_html):
        """Uses 'Annex A (Informative) Acknowledgement' (singular) — now detected."""
        result = spec_validator.content_struct(fapi_html)
        assert result["structure"]["ACKNOWLEDGEMENTS"] is True


# ===================================================================
# E2E test: run process.py against the FAPI file
# ===================================================================


def test_process_py_on_fapi(tmp_path, fapi_html):
    """Run process.py against the FAPI baseline draft 11 spec.

    Expected failures:
    - Content state (DRAFT_ERRATA) does not match filename state (DRAFT)
    - Missing sections (ABSTRACT only — pandoc uses CSS class, not heading)
    """
    md_content = "---\ntitle: FAPI security profile 1.0\n---\n\nPlaceholder markdown.\n"

    spec_files = {
        "fapi/" + FILENAME: fapi_html,
        "fapi/openid-financial-api-part-1-1_0-11.md": md_content,
    }

    csv_content = "Filename,Date,Size\n"
    repo_path, scripts_path = create_test_repo(
        tmp_path, spec_files, spec_list_csv_content=csv_content,
    )
    result = run_python_script("process.py", repo_path, scripts_path)

    assert result.returncode == 1, (
        f"Expected exit 1 but got {result.returncode}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )

    clean = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout)
    fail_lines = [line.strip() for line in clean.splitlines() if line.strip().startswith("FAIL:")]

    # Verify key expected failures are present
    assert any("Missing sections" in f for f in fail_lines), (
        f"Expected 'Missing sections' failure.\nAll FAIL lines:\n"
        + "\n".join(f"  {f}" for f in fail_lines)
    )
    assert any("did not pass all checks" in f for f in fail_lines), (
        f"Expected summary failure line.\nAll FAIL lines:\n"
        + "\n".join(f"  {f}" for f in fail_lines)
    )
