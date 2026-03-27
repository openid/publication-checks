"""Tests for content_struct() from cli-tool.py."""

import importlib
import textwrap

cli_tool = importlib.import_module("cli-tool")


REQUIRED_SECTIONS = [
    "ABSTRACT",
    "INTRODUCTION",
    "REFERENCES",
    "NORMATIVE_REFERENCES",
    "ACKNOWLEDGEMENTS",
    "SECURITY",
]
OPTIONAL_SECTIONS = ["INFORMATIVE_REFERENCES"]


class TestContentStructAllPresent:
    """Test content_struct with a fully valid document."""

    def test_all_sections_present(self, draft_html):
        """All required and optional sections are detected in a complete document."""
        result = cli_tool.content_struct(draft_html)
        for section in REQUIRED_SECTIONS + OPTIONAL_SECTIONS:
            assert result["structure"][section] is True, f"{section} should be present"

    def test_no_missing_required(self, draft_html):
        """A complete document has no missing required sections."""
        result = cli_tool.content_struct(draft_html)
        assert result["missing_required"] == []

    def test_no_missing_optional(self, draft_html):
        """A complete document has no missing optional sections."""
        result = cli_tool.content_struct(draft_html)
        assert result["missing_optional"] == []

    def test_no_warnings(self, draft_html):
        """A complete document produces no warnings."""
        result = cli_tool.content_struct(draft_html)
        assert result["warnings"] == []


class TestContentStructMissingSections:
    """Test content_struct with incomplete documents."""

    def test_missing_required_detected(self, malformed_html):
        """Malformed HTML (include_all_sections=False) is missing required sections."""
        result = cli_tool.content_struct(malformed_html)
        assert len(result["missing_required"]) > 0

    def test_missing_required_sections_listed(self, malformed_html):
        """Specific required sections that are absent appear in missing_required."""
        result = cli_tool.content_struct(malformed_html)
        # malformed_html has include_all_sections=False, so it lacks INTRODUCTION,
        # REFERENCES, NORMATIVE_REFERENCES, SECURITY, ACKNOWLEDGEMENTS
        for section in ["INTRODUCTION", "REFERENCES", "NORMATIVE_REFERENCES",
                        "SECURITY", "ACKNOWLEDGEMENTS"]:
            assert section in result["missing_required"], (
                f"{section} should be in missing_required"
            )

    def test_missing_optional_is_warning_not_error(self, malformed_html):
        """Missing optional sections appear in missing_optional and warnings, not missing_required."""
        result = cli_tool.content_struct(malformed_html)
        assert "INFORMATIVE_REFERENCES" in result["missing_optional"]
        assert "INFORMATIVE_REFERENCES" not in result["missing_required"]
        assert any("INFORMATIVE_REFERENCES" in w for w in result["warnings"])

    def test_abstract_still_present_in_malformed(self, malformed_html):
        """Even the malformed fixture includes an abstract section."""
        result = cli_tool.content_struct(malformed_html)
        assert result["structure"]["ABSTRACT"] is True


class TestContentStructIndividualSections:
    """Test that each required section is individually detected by its regex pattern."""

    def test_abstract_detected(self, draft_html):
        """ABSTRACT section is detected."""
        result = cli_tool.content_struct(draft_html)
        assert result["structure"]["ABSTRACT"] is True

    def test_introduction_detected(self, draft_html):
        """INTRODUCTION section is detected."""
        result = cli_tool.content_struct(draft_html)
        assert result["structure"]["INTRODUCTION"] is True

    def test_references_detected(self, draft_html):
        """REFERENCES section is detected."""
        result = cli_tool.content_struct(draft_html)
        assert result["structure"]["REFERENCES"] is True

    def test_normative_references_detected(self, draft_html):
        """NORMATIVE_REFERENCES section is detected."""
        result = cli_tool.content_struct(draft_html)
        assert result["structure"]["NORMATIVE_REFERENCES"] is True

    def test_acknowledgements_detected(self, draft_html):
        """ACKNOWLEDGEMENTS section is detected."""
        result = cli_tool.content_struct(draft_html)
        assert result["structure"]["ACKNOWLEDGEMENTS"] is True

    def test_security_detected(self, draft_html):
        """SECURITY section is detected."""
        result = cli_tool.content_struct(draft_html)
        assert result["structure"]["SECURITY"] is True

    def test_informative_references_detected(self, draft_html):
        """INFORMATIVE_REFERENCES optional section is detected."""
        result = cli_tool.content_struct(draft_html)
        assert result["structure"]["INFORMATIVE_REFERENCES"] is True


class TestContentStructDebug:
    """Test debug mode for content_struct."""

    def test_debug_populates_section_info(self, draft_html):
        """When debug=True, each section gets pattern, match, and required info."""
        result = cli_tool.content_struct(draft_html, debug=True)
        for section in REQUIRED_SECTIONS + OPTIONAL_SECTIONS:
            assert section in result["debug"], f"debug should contain {section}"
            assert "pattern" in result["debug"][section]
            assert "match" in result["debug"][section]
            assert "required" in result["debug"][section]

    def test_debug_required_flag_correct(self, draft_html):
        """Debug info correctly flags which sections are required vs optional."""
        result = cli_tool.content_struct(draft_html, debug=True)
        for section in REQUIRED_SECTIONS:
            assert result["debug"][section]["required"] is True
        for section in OPTIONAL_SECTIONS:
            assert result["debug"][section]["required"] is False

    def test_debug_match_not_none_for_present_sections(self, draft_html):
        """Debug match is not None for sections that are present."""
        result = cli_tool.content_struct(draft_html, debug=True)
        for section in REQUIRED_SECTIONS + OPTIONAL_SECTIONS:
            assert result["debug"][section]["match"] is not None, (
                f"debug match for {section} should not be None"
            )

    def test_debug_match_none_for_missing_sections(self, malformed_html):
        """Debug match is None for sections that are missing."""
        result = cli_tool.content_struct(malformed_html, debug=True)
        for section in result["missing_required"]:
            assert result["debug"][section]["match"] is None, (
                f"debug match for missing {section} should be None"
            )
