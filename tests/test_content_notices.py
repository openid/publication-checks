"""Tests for content_notices() from cli-tool.py."""

import importlib
import textwrap

cli_tool = importlib.import_module("cli-tool")


class TestContentNoticesValid:
    """Test content_notices with a valid, complete document."""

    def test_notices_present(self, draft_html):
        """A valid document has notices=True."""
        result = cli_tool.content_notices(draft_html)
        assert result["notices"] is True

    def test_license_text_present(self, draft_html):
        """A valid document has license_text_present=True."""
        result = cli_tool.content_notices(draft_html)
        assert result["license_text_present"] is True

    def test_years_match(self, draft_html):
        """A valid document has years_match=True when copyright and published year are the same."""
        result = cli_tool.content_notices(draft_html)
        assert result["years_match"] is True

    def test_copyright_year_extracted(self, draft_html):
        """Copyright year is extracted as an integer from the notices section."""
        result = cli_tool.content_notices(draft_html)
        assert result["copyright_year"] == 2026

    def test_published_year_extracted(self, draft_html):
        """Published year is extracted as an integer from the published date element."""
        result = cli_tool.content_notices(draft_html)
        assert result["published_year"] == 2026


class TestContentNoticesMissing:
    """Test content_notices with documents missing notices."""

    def test_no_notices_section(self, bad_notices_html):
        """A document without a notices section has notices=False."""
        result = cli_tool.content_notices(bad_notices_html)
        assert result["notices"] is False

    def test_no_notices_missing_license_text(self, bad_notices_html):
        """A document without a notices section has license_text_present=False."""
        result = cli_tool.content_notices(bad_notices_html)
        assert result["license_text_present"] is False

    def test_notices_present_but_license_phrases_missing(self):
        """A document with a Notices heading but missing license phrases has license_text_present=False."""
        html = textwrap.dedent("""\
        <!DOCTYPE html>
        <html>
        <head><title>Test Spec</title></head>
        <body>
        <h1 id="title">Test Spec</h1>
        <dd class="published">
          <time datetime="2026-03-20">2026-03-20</time>
        </dd>
        <a href="#name-notices" class="section-name selfRef">Notices</a>
        <p>Copyright (c) 2026 The OpenID Foundation</p>
        <p>This is not the real license text.</p>
        </body>
        </html>
        """)
        result = cli_tool.content_notices(html)
        assert result["notices"] is True
        assert result["license_text_present"] is False


class TestContentNoticesYears:
    """Test year matching logic in content_notices."""

    def test_years_match_false_when_different(self):
        """years_match is False when copyright and published years differ."""
        html = textwrap.dedent("""\
        <!DOCTYPE html>
        <html>
        <head><title>Test Spec</title></head>
        <body>
        <h1 id="title">Test Spec</h1>
        <dd class="published">
          <time datetime="2025-03-20">2025-03-20</time>
        </dd>
        <p>Copyright (c) 2024 The OpenID Foundation</p>
        </body>
        </html>
        """)
        result = cli_tool.content_notices(html)
        assert result["copyright_year"] == 2024
        assert result["published_year"] == 2025
        assert result["years_match"] is False

    def test_years_match_false_when_copyright_missing(self, malformed_html):
        """years_match is False when copyright year is not present."""
        result = cli_tool.content_notices(malformed_html)
        assert result["copyright_year"] is None
        assert result["years_match"] is False


class TestContentNoticesDebug:
    """Test debug output for content_notices."""

    def test_debug_populates_info(self, draft_html):
        """When debug=True, the debug dict contains pattern match details."""
        result = cli_tool.content_notices(draft_html, debug=True)
        assert "NOTICES" in result["debug"]
        assert "COPYRIGHT" in result["debug"]
        assert "PUBLISHED_DATE" in result["debug"]
        assert "LICENSE_TEXT" in result["debug"]
        assert "YEARS_MATCH" in result["debug"]
