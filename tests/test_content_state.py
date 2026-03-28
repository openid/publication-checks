import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import spec_validator


class TestContentDraft:
    """Test DRAFT detection from HTML content."""

    def test_draft_from_fixture(self, draft_html):
        result = spec_validator.content_state(draft_html)
        assert result["state"] == "DRAFT"

    def test_draft_title_with_version_prefix(self):
        html = (
            "<html><head>"
            "<title>OpenID Connect Example 1.0 - Draft 01</title>"
            "</head><body>"
            "<h1>OpenID Connect Example 1.0 - Draft 01</h1>"
            "</body></html>"
        )
        result = spec_validator.content_state(html)
        assert result["state"] == "DRAFT"

    def test_draft_high_number(self):
        html = (
            "<html><head>"
            "<title>OpenID Federation 1.0 - Draft 42</title>"
            "</head><body>"
            "<h1>OpenID Federation 1.0 - Draft 42</h1>"
            "</body></html>"
        )
        result = spec_validator.content_state(html)
        assert result["state"] == "DRAFT"

    def test_draft_uppercase_d(self):
        html = (
            "<html><head>"
            "<title>OpenID Connect 1.0 - Draft 05</title>"
            "</head><body>"
            "<h1>OpenID Connect 1.0 - Draft 05</h1>"
            "</body></html>"
        )
        result = spec_validator.content_state(html)
        assert result["state"] == "DRAFT"

    def test_draft_lowercase_d(self):
        html = (
            "<html><head>"
            "<title>OpenID Connect 1.0 - draft 03</title>"
            "</head><body>"
            "<h1>OpenID Connect 1.0 - draft 03</h1>"
            "</body></html>"
        )
        result = spec_validator.content_state(html)
        assert result["state"] == "DRAFT"


class TestContentErrata:
    """Test ERRATA detection from HTML content."""

    def test_errata_from_fixture(self, errata_html):
        result = spec_validator.content_state(errata_html)
        assert result["state"] == "ERRATA"

    def test_errata_set_in_title(self):
        html = (
            "<html><head>"
            "<title>OpenID Example incorporating errata set 1</title>"
            "</head><body>"
            "<h1>OpenID Example incorporating errata set 1</h1>"
            "</body></html>"
        )
        result = spec_validator.content_state(html)
        assert result["state"] == "ERRATA"

    def test_errata_higher_number(self):
        html = (
            "<html><head>"
            "<title>OpenID Connect Core errata set 3</title>"
            "</head><body>"
            "<h1>OpenID Connect Core errata set 3</h1>"
            "</body></html>"
        )
        result = spec_validator.content_state(html)
        assert result["state"] == "ERRATA"

    def test_errata_alternative_format(self):
        """Errata pattern also matches 'errata' followed by a number."""
        html = (
            "<html><head>"
            "<title>OpenID Connect Core errata 2</title>"
            "</head><body>"
            "<h1>OpenID Connect Core errata 2</h1>"
            "</body></html>"
        )
        result = spec_validator.content_state(html)
        assert result["state"] == "ERRATA"


class TestContentFinal:
    """Test FINAL detection from HTML content."""

    def test_final_from_fixture(self, final_html):
        result = spec_validator.content_state(final_html)
        assert result["state"] == "FINAL"

    def test_final_via_intended_status(self):
        """Newer xml2rfc specs use <dd class="intended-status">Final</dd>."""
        html = (
            "<html><head>"
            "<title>OpenID Example 1.0</title>"
            "</head><body>"
            "<h1>OpenID Example 1.0</h1>"
            '<dd class="intended-status">Final</dd>'
            "</body></html>"
        )
        result = spec_validator.content_state(html)
        assert result["state"] == "FINAL"

    def test_final_via_status_class(self):
        """Some xml2rfc specs use <dd class="status">Final</dd> (without 'intended-')."""
        html = (
            "<html><head>"
            "<title>OpenID Example 1.0</title>"
            "</head><body>"
            "<h1>OpenID Example 1.0</h1>"
            '<dd class="status">Final</dd>'
            "</body></html>"
        )
        result = spec_validator.content_state(html)
        assert result["state"] == "FINAL"

    def test_final_via_header_table(self):
        """Older specs use <td class="header">Final</td>."""
        html = (
            "<html><head>"
            "<title>OpenID Connect Core 1.0</title>"
            "</head><body>"
            "<h1>OpenID Connect Core 1.0</h1>"
            '<td class="header">Final</td>'
            "</body></html>"
        )
        result = spec_validator.content_state(html)
        assert result["state"] == "FINAL"

    def test_1_0_in_title_is_not_final(self):
        """A title containing '1.0' should NOT be detected as FINAL (old bug)."""
        html = (
            "<html><head>"
            "<title>OpenID Example 1.0</title>"
            "</head><body>"
            "<h1>OpenID Example 1.0</h1>"
            "</body></html>"
        )
        result = spec_validator.content_state(html)
        assert result["state"] != "FINAL"


class TestContentImplementers:
    """Test IMPLEMENTERS detection from HTML content.

    The IMPLEMENTERS_CONTENT pattern matches "Implementers Draft N" specifically.
    IMPLEMENTERS is checked before DRAFT in the state_order, so a title like
    "Implementers Draft 2" resolves to IMPLEMENTERS, not DRAFT.
    """

    def test_implementers_fixture_resolves_to_implementers(self, implementers_html):
        """The conftest fixture title is 'Implementers Draft 1', so IMPLEMENTERS wins."""
        result = spec_validator.content_state(implementers_html)
        assert result["state"] == "IMPLEMENTERS"

    def test_implementers_draft_2(self):
        """'Implementers Draft 2' should resolve to IMPLEMENTERS."""
        html = (
            "<html><head>"
            "<title>OpenID Example 1.0 - Implementers Draft 2</title>"
            "</head><body>"
            "<h1>OpenID Example 1.0 - Implementers Draft 2</h1>"
            "</body></html>"
        )
        result = spec_validator.content_state(html)
        assert result["state"] == "IMPLEMENTERS"

    def test_implementers_beats_draft_when_both_present(self):
        """When 'Implementers Draft N' is in the title, IMPLEMENTERS wins over DRAFT."""
        html = (
            "<html><head>"
            "<title>OpenID Example 1.0 - Implementers Draft 1</title>"
            "</head><body>"
            "<h1>OpenID Example 1.0 - Implementers Draft 1</h1>"
            "</body></html>"
        )
        result = spec_validator.content_state(html)
        assert result["state"] == "IMPLEMENTERS"

    def test_plain_draft_still_resolves_to_draft(self):
        """A plain 'Draft 01' title (no 'Implementers') still resolves to DRAFT."""
        html = (
            "<html><head>"
            "<title>OpenID Example 1.0 - Draft 01</title>"
            "</head><body>"
            "<h1>OpenID Example 1.0 - Draft 01</h1>"
            "</body></html>"
        )
        result = spec_validator.content_state(html)
        assert result["state"] == "DRAFT"


class TestContentUnknown:
    """Test that UNKNOWN is returned when content is missing required tags."""

    def test_no_title_or_h1(self):
        html = "<html><head></head><body><p>Hello</p></body></html>"
        result = spec_validator.content_state(html)
        assert result["state"] == "UNKNOWN"

    def test_title_exists_but_no_h1(self):
        html = (
            "<html><head>"
            "<title>OpenID Connect Core 1.0 - Draft 01</title>"
            "</head><body>"
            "<p>No heading here</p>"
            "</body></html>"
        )
        result = spec_validator.content_state(html)
        assert result["state"] == "UNKNOWN"

    def test_h1_exists_but_no_title(self):
        html = (
            "<html><head></head><body>"
            "<h1>OpenID Connect Core 1.0 - Draft 01</h1>"
            "</body></html>"
        )
        result = spec_validator.content_state(html)
        assert result["state"] == "UNKNOWN"

    def test_empty_content(self):
        result = spec_validator.content_state("")
        assert result["state"] == "UNKNOWN"


class TestContentReleased:
    """Test that RELEASED is returned when title+h1 exist but no state pattern matches."""

    def test_released_generic_title(self):
        html = (
            "<html><head>"
            "<title>OpenID Some Specification</title>"
            "</head><body>"
            "<h1>OpenID Some Specification</h1>"
            "</body></html>"
        )
        result = spec_validator.content_state(html)
        assert result["state"] == "RELEASED"

    def test_released_no_state_keywords(self):
        html = (
            "<html><head>"
            "<title>A Document With No State Keywords</title>"
            "</head><body>"
            "<h1>A Document With No State Keywords</h1>"
            "</body></html>"
        )
        result = spec_validator.content_state(html)
        assert result["state"] == "RELEASED"


class TestContentErrataBeforeDraft:
    """Test that ERRATA is checked before DRAFT in state detection order."""

    def test_errata_takes_priority_over_draft(self):
        """A title containing both 'errata' and 'draft' should resolve to ERRATA."""
        html = (
            "<html><head>"
            "<title>OpenID Connect 1.0 Draft errata set 2</title>"
            "</head><body>"
            "<h1>OpenID Connect 1.0 Draft errata set 2</h1>"
            "</body></html>"
        )
        result = spec_validator.content_state(html)
        assert result["state"] == "ERRATA"


class TestContentDebugMode:
    """Test that debug mode populates extra information."""

    def test_debug_includes_title_tag(self, draft_html):
        result = spec_validator.content_state(draft_html, debug=True)
        assert "TITLE_TAG" in result["debug"]
        assert result["debug"]["TITLE_TAG"]["match"] is not None

    def test_debug_includes_h1_title(self, draft_html):
        result = spec_validator.content_state(draft_html, debug=True)
        assert "H1_TITLE" in result["debug"]
        assert result["debug"]["H1_TITLE"]["match"] is not None

    def test_debug_includes_content_patterns(self, draft_html):
        result = spec_validator.content_state(draft_html, debug=True)
        assert "DRAFT_CONTENT" in result["debug"]
        assert result["debug"]["DRAFT_CONTENT"]["match"] is not None

    def test_debug_off_empty(self, draft_html):
        result = spec_validator.content_state(draft_html, debug=False)
        assert result["debug"] == {}

    def test_debug_shows_all_content_patterns(self, final_html):
        result = spec_validator.content_state(final_html, debug=True)
        for key in ["ERRATA_CONTENT", "DRAFT_CONTENT", "IMPLEMENTERS_CONTENT", "FINAL_CONTENT"]:
            assert key in result["debug"]


class TestContentReturnStructure:
    """Test the return value structure."""

    def test_return_has_state_key(self):
        result = spec_validator.content_state("<html></html>")
        assert "state" in result

    def test_return_has_debug_key(self):
        result = spec_validator.content_state("<html></html>")
        assert "debug" in result

    def test_return_is_dict(self):
        result = spec_validator.content_state("<html></html>")
        assert isinstance(result, dict)
