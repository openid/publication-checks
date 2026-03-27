import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import spec_validator


class TestFilenameDraft:
    """Test that DRAFT filenames are recognised correctly."""

    def test_simple_draft(self):
        result = spec_validator.filename_state("openid-connect-core-1_0-01.html")
        assert result["state"] == "DRAFT"

    def test_high_draft_number(self):
        result = spec_validator.filename_state("openid-connect-core-1_0-99.html")
        assert result["state"] == "DRAFT"

    def test_single_digit_draft(self):
        result = spec_validator.filename_state("openid-connect-core-1_0-5.html")
        assert result["state"] == "DRAFT"

    def test_draft_different_spec(self):
        result = spec_validator.filename_state("openid-federation-1_0-03.html")
        assert result["state"] == "DRAFT"

    def test_draft_with_longer_name(self):
        result = spec_validator.filename_state("openid-connect-self-issued-v2-1_0-12.html")
        assert result["state"] == "DRAFT"


class TestFilenameFinal:
    """Test that FINAL filenames are recognised correctly."""

    def test_simple_final(self):
        result = spec_validator.filename_state("openid-connect-core-1_0-final.html")
        assert result["state"] == "FINAL"

    def test_final_different_spec(self):
        result = spec_validator.filename_state("openid-federation-1_0-final.html")
        assert result["state"] == "FINAL"

    def test_final_long_name(self):
        result = spec_validator.filename_state("openid-connect-self-issued-v2-1_0-final.html")
        assert result["state"] == "FINAL"


class TestFilenameErrata:
    """Test that ERRATA filenames are recognised correctly."""

    def test_errata_single_digit(self):
        result = spec_validator.filename_state("openid-connect-core-1_0-errata1.html")
        assert result["state"] == "ERRATA"

    def test_errata_multi_digit(self):
        result = spec_validator.filename_state("openid-connect-core-1_0-errata12.html")
        assert result["state"] == "ERRATA"

    def test_errata_different_spec(self):
        result = spec_validator.filename_state("openid-federation-1_0-errata3.html")
        assert result["state"] == "ERRATA"


class TestFilenameImplementors:
    """Test that IMPLEMENTORS filenames are recognised correctly."""

    def test_implementors_draft(self):
        result = spec_validator.filename_state("openid-connect-core-1_0-ID1.html")
        assert result["state"] == "IMPLEMENTORS"

    def test_implementors_higher_number(self):
        result = spec_validator.filename_state("openid-connect-core-1_0-ID3.html")
        assert result["state"] == "IMPLEMENTORS"

    def test_implementors_different_spec(self):
        result = spec_validator.filename_state("openid-federation-1_0-ID2.html")
        assert result["state"] == "IMPLEMENTORS"


class TestFilenameCurrent:
    """Test that CURRENT filenames (no state suffix) are recognised correctly."""

    def test_current_simple(self):
        result = spec_validator.filename_state("openid-connect-core-1_0.html")
        assert result["state"] == "CURRENT"

    def test_current_different_spec(self):
        result = spec_validator.filename_state("openid-federation-1_0.html")
        assert result["state"] == "CURRENT"

    def test_current_long_name(self):
        result = spec_validator.filename_state("openid-connect-self-issued-v2-1_0.html")
        assert result["state"] == "CURRENT"


class TestFilenameUnknown:
    """Test that invalid filenames return UNKNOWN."""

    def test_plain_text_file(self):
        result = spec_validator.filename_state("readme.txt")
        assert result["state"] == "UNKNOWN"

    def test_uppercase_start(self):
        """The DRAFT pattern uses \\w which matches uppercase, so this is DRAFT."""
        result = spec_validator.filename_state("UPPERCASE-1_0-01.html")
        assert result["state"] == "DRAFT"

    def test_missing_version(self):
        result = spec_validator.filename_state("openid-connect-core.html")
        assert result["state"] == "UNKNOWN"

    def test_empty_string(self):
        result = spec_validator.filename_state("")
        assert result["state"] == "UNKNOWN"

    def test_no_extension(self):
        result = spec_validator.filename_state("openid-connect-core-1_0-01")
        assert result["state"] == "UNKNOWN"

    def test_wrong_extension(self):
        result = spec_validator.filename_state("openid-connect-core-1_0-01.pdf")
        assert result["state"] == "UNKNOWN"

    def test_three_digit_draft_number(self):
        """Draft number must be 1-2 digits, so 3 digits should fail."""
        result = spec_validator.filename_state("openid-connect-core-1_0-123.html")
        assert result["state"] == "UNKNOWN"

    def test_random_suffix(self):
        result = spec_validator.filename_state("openid-connect-core-1_0-beta.html")
        assert result["state"] == "UNKNOWN"


class TestFilenameDebugMode:
    """Test that debug mode populates the debug dict."""

    def test_debug_on_match(self):
        result = spec_validator.filename_state("openid-connect-core-1_0-01.html", debug=True)
        assert result["state"] == "DRAFT"
        # The matching state should have pattern and match info
        assert "DRAFT" in result["debug"]
        assert result["debug"]["DRAFT"]["pattern"] is not None
        assert result["debug"]["DRAFT"]["match"] is not None

    def test_debug_on_no_match(self):
        result = spec_validator.filename_state("readme.txt", debug=True)
        assert result["state"] == "UNKNOWN"
        # All states should appear in debug with match=None
        for state in ["CURRENT", "DRAFT", "IMPLEMENTORS", "ERRATA", "FINAL"]:
            assert state in result["debug"]
            assert result["debug"][state]["match"] is None

    def test_debug_off_empty(self):
        result = spec_validator.filename_state("openid-connect-core-1_0-01.html", debug=False)
        assert result["debug"] == {}

    def test_debug_shows_earlier_failed_patterns(self):
        """When DRAFT matches, CURRENT (checked first) should show match=None in debug."""
        result = spec_validator.filename_state("openid-connect-core-1_0-01.html", debug=True)
        assert result["state"] == "DRAFT"
        assert "CURRENT" in result["debug"]
        assert result["debug"]["CURRENT"]["match"] is None


class TestFilenameReturnStructure:
    """Test the return value structure."""

    def test_return_has_state_key(self):
        result = spec_validator.filename_state("anything")
        assert "state" in result

    def test_return_has_debug_key(self):
        result = spec_validator.filename_state("anything")
        assert "debug" in result

    def test_return_is_dict(self):
        result = spec_validator.filename_state("openid-connect-core-1_0.html")
        assert isinstance(result, dict)
