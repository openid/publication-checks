import importlib
import os
import sys

import pytest

# Import the module with a hyphenated name
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
cli_tool = importlib.import_module("cli-tool")


# ---------------------------------------------------------------------------
# All tests in this file are marked xfail because content_filename_match()
# has multiple bugs:
#   1. Line 754 references PATTERNS['TITLE'] which does not exist -- the
#      correct key is PATTERNS['TITLE_TAG'].  This raises KeyError.
#   2. Line 750 calls match.group(2) for DRAFT filenames whose regex has no
#      second capture group, raising IndexError.
#
# The tests document the *expected correct* behaviour so that they will start
# passing once both bugs are fixed.
# ---------------------------------------------------------------------------

BUG_REASON = (
    "Bug: references non-existent PATTERNS['TITLE'], "
    "should be PATTERNS['TITLE_TAG']"
)


def _build_content(title):
    """Return minimal HTML content with matching <title> and <h1> tags."""
    return (
        f"<html><head><title>{title}</title></head>"
        f'<body><h1 id="title">{title}</h1></body></html>'
    )


@pytest.mark.xfail(reason=BUG_REASON, raises=(KeyError, IndexError))
class TestDraftFilenameMatch:
    """DRAFT filename paired with DRAFT content should match."""

    def test_draft_filename_draft_content(self):
        content = _build_content("OpenID Connect Example 1.0 - Draft 01")
        result = cli_tool.content_filename_match(
            content, "openid-connect-example-1_0-01.html"
        )
        assert result["match"] is True

    def test_draft_higher_number(self):
        content = _build_content("OpenID Connect Example 1.0 - Draft 05")
        result = cli_tool.content_filename_match(
            content, "openid-connect-example-1_0-05.html"
        )
        assert result["match"] is True


@pytest.mark.xfail(reason=BUG_REASON, raises=(KeyError, IndexError))
class TestFinalFilenameMatch:
    """FINAL filename paired with FINAL content should match."""

    def test_final_filename_final_content(self):
        content = _build_content("Final: OpenID Connect Example 1.0")
        result = cli_tool.content_filename_match(
            content, "openid-connect-example-1_0-final.html"
        )
        assert result["match"] is True


@pytest.mark.xfail(reason=BUG_REASON, raises=(KeyError, IndexError))
class TestMismatchedTypes:
    """Filename type and content type differ -- should NOT match."""

    def test_draft_filename_final_content(self):
        content = _build_content("Final: OpenID Connect Example 1.0")
        result = cli_tool.content_filename_match(
            content, "openid-connect-example-1_0-01.html"
        )
        assert result["match"] is False

    def test_final_filename_draft_content(self):
        content = _build_content("OpenID Connect Example 1.0 - Draft 01")
        result = cli_tool.content_filename_match(
            content, "openid-connect-example-1_0-final.html"
        )
        assert result["match"] is False


@pytest.mark.xfail(reason=BUG_REASON, raises=(KeyError, IndexError))
class TestVersionNumberMismatch:
    """When types agree but version numbers differ, match should be False."""

    def test_draft_number_mismatch(self):
        content = _build_content("OpenID Connect Example 1.0 - Draft 03")
        result = cli_tool.content_filename_match(
            content, "openid-connect-example-1_0-01.html"
        )
        assert result["match"] is False


@pytest.mark.xfail(reason=BUG_REASON, raises=(KeyError, IndexError))
class TestErrataFilenameMatch:
    """ERRATA filename paired with ERRATA content should match."""

    def test_errata_match(self):
        content = _build_content(
            "OpenID Connect Example 1.0 incorporating errata set 1"
        )
        result = cli_tool.content_filename_match(
            content, "openid-connect-example-1_0-errata1.html"
        )
        assert result["match"] is True

    def test_errata_number_mismatch(self):
        content = _build_content(
            "OpenID Connect Example 1.0 incorporating errata set 2"
        )
        result = cli_tool.content_filename_match(
            content, "openid-connect-example-1_0-errata1.html"
        )
        assert result["match"] is False


@pytest.mark.xfail(reason=BUG_REASON, raises=(KeyError, IndexError))
class TestDebugOutput:
    """Debug mode should populate extra information in the result."""

    def test_debug_contains_types(self):
        content = _build_content("OpenID Connect Example 1.0 - Draft 01")
        result = cli_tool.content_filename_match(
            content, "openid-connect-example-1_0-01.html", debug=True
        )
        assert "debug" in result
        assert "Filename Type" in result["debug"]
        assert "Content Type" in result["debug"]

    def test_debug_off_has_no_debug_key(self):
        content = _build_content("OpenID Connect Example 1.0 - Draft 01")
        result = cli_tool.content_filename_match(
            content, "openid-connect-example-1_0-01.html", debug=False
        )
        assert "debug" not in result
