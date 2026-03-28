"""Tests for content_date() from spec_validator.py."""

import textwrap

import spec_validator


class TestContentDateExtraction:
    """Test date extraction from HTML content."""

    def test_extract_published_date(self, draft_html):
        """Published date is extracted from <dd class="published"><time datetime="..."> format."""
        result, _ = spec_validator.content_date(draft_html)
        assert result["date"] == "2026-03-20"

    def test_extract_copyright_year(self, draft_html):
        """Copyright year is extracted from 'Copyright (c) YYYY The OpenID Foundation'."""
        result, _ = spec_validator.content_date(draft_html)
        assert result["copyright_date"] == "2026"

    def test_years_match_when_same(self, draft_html):
        """years_match is True when copyright year matches published year."""
        result, _ = spec_validator.content_date(draft_html)
        assert result["years_match"] is True

    def test_years_do_not_match_when_different(self):
        """years_match is False when copyright year differs from published year."""
        html = textwrap.dedent("""\
        <!DOCTYPE html>
        <html>
        <head><title>Test Spec</title></head>
        <body>
        <h1 id="title">Test Spec</h1>
        <dd class="published">
          <time datetime="2025-06-15">2025-06-15</time>
        </dd>
        <p>Copyright (c) 2024 The OpenID Foundation</p>
        </body>
        </html>
        """)
        result, _ = spec_validator.content_date(html)
        assert result["years_match"] is False
        assert result["date"] == "2025-06-15"
        assert result["copyright_date"] == "2024"
        assert "must match" in result["error"]

    def test_missing_date_returns_not_found(self):
        """When no date element exists, result['date'] is 'Date not found'."""
        html = textwrap.dedent("""\
        <!DOCTYPE html>
        <html>
        <head><title>No Date Spec</title></head>
        <body>
        <h1 id="title">No Date Spec</h1>
        <p>Copyright (c) 2026 The OpenID Foundation</p>
        </body>
        </html>
        """)
        result, _ = spec_validator.content_date(html)
        assert result["date"] == "Date not found"


class TestContentDateComparison:
    """Test compare_date functionality."""

    def test_comparison_calculates_days_difference(self, draft_html):
        """Passing compare_date adds a 'comparison' key with correct days_difference."""
        result, _ = spec_validator.content_date(draft_html, compare_date="2026-03-27")
        assert "comparison" in result
        assert result["comparison"]["days_difference"] == 7
        assert result["comparison"]["compare_date"] == "2026-03-27"
        assert result["comparison"]["status"] == "ahead"

    def test_comparison_same_date(self, draft_html):
        """When compare_date equals published date, days_difference is 0 and status is 'same'."""
        result, _ = spec_validator.content_date(draft_html, compare_date="2026-03-20")
        assert result["comparison"]["days_difference"] == 0
        assert result["comparison"]["status"] == "same"

    def test_comparison_behind(self, draft_html):
        """When compare_date is before published date, status is 'behind'."""
        result, _ = spec_validator.content_date(draft_html, compare_date="2026-03-10")
        assert result["comparison"]["days_difference"] == 10
        assert result["comparison"]["status"] == "behind"


class TestContentDateExitCodes:
    """Test exit codes returned by content_date."""

    def test_exit_success_when_years_match(self, draft_html):
        """Exit code is EXIT_SUCCESS (0) when years match."""
        _, exit_code = spec_validator.content_date(draft_html)
        assert exit_code == spec_validator.EXIT_SUCCESS

    def test_exit_error_when_years_mismatch(self):
        """Exit code is EXIT_CONTENT_DATE_ERROR (30) when years don't match."""
        html = textwrap.dedent("""\
        <!DOCTYPE html>
        <html>
        <head><title>Test Spec</title></head>
        <body>
        <h1 id="title">Test Spec</h1>
        <dd class="published">
          <time datetime="2025-06-15">2025-06-15</time>
        </dd>
        <p>Copyright (c) 2024 The OpenID Foundation</p>
        </body>
        </html>
        """)
        _, exit_code = spec_validator.content_date(html)
        assert exit_code == spec_validator.EXIT_CONTENT_DATE_ERROR
        assert exit_code == 30

    def test_exit_error_when_no_dates_found(self):
        """Exit code is EXIT_CONTENT_DATE_ERROR when no dates are found (years_match stays False)."""
        html = "<html><body><p>Nothing here</p></body></html>"
        _, exit_code = spec_validator.content_date(html)
        assert exit_code == spec_validator.EXIT_CONTENT_DATE_ERROR


class TestContentDateDebug:
    """Test debug output."""

    def test_debug_populates_info(self, draft_html):
        """When debug=True, the debug dict contains pattern match information."""
        result, _ = spec_validator.content_date(draft_html, debug=True)
        assert "PUBLISHED_DATE" in result["debug"]
        assert result["debug"]["PUBLISHED_DATE"]["match"] is not None
        assert "COPYRIGHT" in result["debug"]
        assert result["debug"]["COPYRIGHT"]["match"] is not None
