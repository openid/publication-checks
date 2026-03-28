import spec_validator


class TestContentHistory:
    """Tests for content_history(content, debug=False)."""

    def test_history_present_in_draft(self, draft_html):
        """draft_html includes a Document History section (format 1)."""
        result = spec_validator.content_history(draft_html)
        assert result["history_present"] is True
        assert result["history"] is not None

    def test_history_not_present(self, no_history_html):
        """no_history_html has include_history=False."""
        result = spec_validator.content_history(no_history_html)
        assert result["history_present"] is False
        assert result["history"] is None

    def test_history_entries_parsed_correctly(self, draft_html):
        """The draft fixture has version -01 with an 'Initial draft' entry."""
        result = spec_validator.content_history(draft_html)
        entries = result["history"]
        assert isinstance(entries, list)
        assert len(entries) > 0
        # The fixture contains <p>-01</p> and <ul><li>Initial draft</li></ul>
        joined = " ".join(entries)
        assert "-01" in joined
        assert "Initial draft" in joined

    def test_second_heading_format_detected(self):
        """Format 2: <h1 id="rfc.appendix.A">..Document History..</h1>"""
        html = """
        <!DOCTYPE html>
        <html><head><title>Test</title></head><body>
        <h1 id="rfc.appendix.A">
          <a href="#rfc.appendix.A">Appendix A.</a>
          <a href="#document-history" id="document-history">Document History</a>
        </h1>
        <p>-02</p>
        <ul><li>Added new section</li></ul>
        <h1>Next Section</h1>
        </body></html>
        """
        result = spec_validator.content_history(html)
        assert result["history_present"] is True
        assert result["history"] is not None
        joined = " ".join(result["history"])
        assert "-02" in joined
        assert "Added new section" in joined

    def test_third_heading_format_detected(self):
        """Format 3: <h3>Appendix A.&nbsp; Document History</h3>"""
        html = """
        <!DOCTYPE html>
        <html><head><title>Test</title></head><body>
        <h3>Appendix A.&nbsp; Document History</h3>
        <p>-03</p>
        <ul><li>Bug fixes</li></ul>
        <h3>Next Section</h3>
        </body></html>
        """
        result = spec_validator.content_history(html)
        assert result["history_present"] is True
        assert result["history"] is not None
        joined = " ".join(result["history"])
        assert "-03" in joined
        assert "Bug fixes" in joined

    def test_debug_mode(self, draft_html):
        """When debug=True, debug dict should contain DOCUMENT_HISTORY info."""
        result = spec_validator.content_history(draft_html, debug=True)
        debug = result["debug"]
        assert "DOCUMENT_HISTORY" in debug
        assert "pattern" in debug["DOCUMENT_HISTORY"]
        assert debug["DOCUMENT_HISTORY"]["match"] is not None
