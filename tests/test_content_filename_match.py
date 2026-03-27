import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import spec_validator


def _build_content(title):
    """Return minimal HTML content with matching <title> and <h1> tags."""
    return (
        f"<html><head><title>{title}</title></head>"
        f'<body><h1 id="title">{title}</h1></body></html>'
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
        content = _build_content("Final: OpenID Connect Example 1.0")
        result = spec_validator.content_filename_match(
            content, "openid-connect-example-1_0-final.html"
        )
        assert result["match"] is True


class TestMismatchedTypes:
    """Filename type and content type differ -- should NOT match."""

    def test_draft_filename_final_content(self):
        content = _build_content("Final: OpenID Connect Example 1.0")
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
