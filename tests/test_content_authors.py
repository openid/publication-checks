import spec_validator


class TestContentAuthors:
    """Tests for content_authors(content, debug=False)."""

    def test_div_format_extraction(self, draft_html):
        """draft_html has two authors in div format: Jane Doe / Example Corp
        and John Smith / Test Inc."""
        result = spec_validator.content_authors(draft_html)
        authors = result["authors"]
        assert len(authors) == 2
        assert authors[0] == {"name": "Jane Doe", "organization": "Example Corp"}
        assert authors[1] == {"name": "John Smith", "organization": "Test Inc"}

    def test_table_format_extraction(self, table_authors_html):
        """table_authors_html has one author in table format: Jane Doe / Example Corp."""
        result = spec_validator.content_authors(table_authors_html)
        authors = result["authors"]
        assert len(authors) == 1
        assert authors[0] == {"name": "Jane Doe", "organization": "Example Corp"}

    def test_no_authors_returns_empty_list(self, malformed_html):
        """malformed_html has include_authors=False, so no authors found."""
        result = spec_validator.content_authors(malformed_html)
        assert result["authors"] == []

    def test_debug_mode_populates_debug_info(self, draft_html):
        """When debug=True, the debug dict should contain pattern match info."""
        result = spec_validator.content_authors(draft_html, debug=True)
        debug = result["debug"]
        # All four debug keys should be present
        assert "AUTHORS_DIV" in debug
        assert "AUTHOR_DIV" in debug
        assert "AUTHORS_TABLE" in debug
        assert "AUTHOR_TABLE_ROW" in debug
        # AUTHOR_DIV uses findall and should find individual author entries
        assert isinstance(debug["AUTHOR_DIV"], list)
