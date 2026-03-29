import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import spec_validator


def _build_content(title, intended_status=None):
    """Return minimal HTML content with matching <title> and <h1> tags."""
    status_html = ""
    if intended_status:
        status_html = f'<dd class="intended-status">{intended_status}</dd>'
    return (
        f"<html><head><title>{title}</title></head>"
        f'<body><h1 id="title">{title}</h1>{status_html}</body></html>'
    )


class TestDraftFilenameMatch:
    """DRAFT filename paired with DRAFT content should match."""

    def test_draft_filename_draft_content(self):
        content = _build_content("OpenID Connect Example 1.0 - Draft 01")
        result = spec_validator.content_filename_match(
            content, "openid-connect-example-1_0-01.html"
        )
        assert result["match"] is True

    def test_draft_higher_number(self):
        content = _build_content("OpenID Connect Example 1.0 - Draft 05")
        result = spec_validator.content_filename_match(
            content, "openid-connect-example-1_0-05.html"
        )
        assert result["match"] is True


class TestFinalFilenameMatch:
    """FINAL filename paired with FINAL content should match."""

    def test_final_filename_final_content(self):
        content = _build_content("OpenID Connect Example 1.0", intended_status="Final")
        result = spec_validator.content_filename_match(
            content, "openid-connect-example-1_0-final.html"
        )
        assert result["match"] is True


class TestMismatchedTypes:
    """Filename type and content type differ -- should NOT match."""

    def test_draft_filename_final_content(self):
        content = _build_content("OpenID Connect Example 1.0", intended_status="Final")
        result = spec_validator.content_filename_match(
            content, "openid-connect-example-1_0-01.html"
        )
        assert result["match"] is False

    def test_final_filename_draft_content(self):
        content = _build_content("OpenID Connect Example 1.0 - Draft 01")
        result = spec_validator.content_filename_match(
            content, "openid-connect-example-1_0-final.html"
        )
        assert result["match"] is False


class TestVersionNumberMismatch:
    """When types agree but version numbers differ, match should be False."""

    def test_draft_number_mismatch(self):
        content = _build_content("OpenID Connect Example 1.0 - Draft 03")
        result = spec_validator.content_filename_match(
            content, "openid-connect-example-1_0-01.html"
        )
        assert result["match"] is False


class TestImplementersFilenameMatch:
    """IMPLEMENTERS filename with DRAFT content should match.

    Implementers Drafts are published by copying draft files with -IDN
    filenames. The title keeps the original 'Draft NN' wording.
    """

    def test_id_filename_with_draft_content(self):
        content = _build_content("OpenID Connect Example 1.0 - draft 02")
        result = spec_validator.content_filename_match(
            content, "openid-connect-example-1_0-ID1.html"
        )
        assert result["match"] is True

    def test_id_filename_with_different_draft_number(self):
        """ID number and draft number are independent - should still match."""
        content = _build_content("OpenID Connect Example 1.0 - Draft 06")
        result = spec_validator.content_filename_match(
            content, "openid-connect-example-1_0-ID2.html"
        )
        assert result["match"] is True

    def test_id_filename_with_final_content_no_match(self):
        """IMPLEMENTERS filename with FINAL content should NOT match."""
        content = _build_content(
            "OpenID Connect Example 1.0", intended_status="Final"
        )
        result = spec_validator.content_filename_match(
            content, "openid-connect-example-1_0-ID1.html"
        )
        assert result["match"] is False


class TestErrataFilenameMatch:
    """ERRATA filename paired with ERRATA content should match."""

    def test_errata_match(self):
        content = _build_content(
            "OpenID Connect Example 1.0 incorporating errata set 1"
        )
        result = spec_validator.content_filename_match(
            content, "openid-connect-example-1_0-errata1.html"
        )
        assert result["match"] is True

    def test_errata_number_mismatch(self):
        content = _build_content(
            "OpenID Connect Example 1.0 incorporating errata set 2"
        )
        result = spec_validator.content_filename_match(
            content, "openid-connect-example-1_0-errata1.html"
        )
        assert result["match"] is False


class TestDebugOutput:
    """Debug mode should populate extra information in the result."""

    def test_debug_contains_types(self):
        content = _build_content("OpenID Connect Example 1.0 - Draft 01")
        result = spec_validator.content_filename_match(
            content, "openid-connect-example-1_0-01.html", debug=True
        )
        assert "debug" in result
        assert "Filename Type" in result["debug"]
        assert "Content Type" in result["debug"]

    def test_debug_off_has_no_debug_key(self):
        content = _build_content("OpenID Connect Example 1.0 - Draft 01")
        result = spec_validator.content_filename_match(
            content, "openid-connect-example-1_0-01.html", debug=False
        )
        assert "debug" not in result
