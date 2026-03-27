import spec_validator


class TestContentTitle:
    """Tests for content_title(content, debug=False)."""

    def test_matching_title_and_h1(self, draft_html):
        """draft_html has the same string in <title> and <h1>."""
        result = spec_validator.content_title(draft_html)
        assert result["match"] is True
        assert result["title_tag"] is not None
        assert result["h1_title"] is not None
        assert result["title_tag"].lower() == result["h1_title"].lower()

    def test_mismatched_title_and_h1(self):
        """When title and h1 differ, match should be False."""
        html = """
        <!DOCTYPE html>
        <html><head><title>Title One</title></head>
        <body><h1 id="title">Title Two</h1></body></html>
        """
        result = spec_validator.content_title(html)
        assert result["match"] is False
        assert result["title_tag"] == "Title One"
        assert result["h1_title"] == "Title Two"

    def test_case_insensitive_comparison(self):
        """Titles that differ only in case should match."""
        html = """
        <!DOCTYPE html>
        <html><head><title>OpenID Connect Example</title></head>
        <body><h1 id="title">openid connect example</h1></body></html>
        """
        result = spec_validator.content_title(html)
        assert result["match"] is True

    def test_missing_title_tag(self):
        """When there is no <title> tag, match should be False and title_tag None."""
        html = """
        <!DOCTYPE html>
        <html><head></head>
        <body><h1 id="title">Some Title</h1></body></html>
        """
        result = spec_validator.content_title(html)
        assert result["match"] is False
        assert result["title_tag"] is None

    def test_missing_h1_tag(self):
        """When there is no <h1> tag, match should be False and h1_title None."""
        html = """
        <!DOCTYPE html>
        <html><head><title>Some Title</title></head>
        <body><p>No heading here.</p></body></html>
        """
        result = spec_validator.content_title(html)
        assert result["match"] is False
        assert result["h1_title"] is None

    def test_debug_mode(self, draft_html):
        """When debug=True, debug dict should contain pattern match info."""
        result = spec_validator.content_title(draft_html, debug=True)
        assert result["debug"] is not None
        assert "TITLE_TAG" in result["debug"]
        assert "H1_TITLE" in result["debug"]
        assert "pattern" in result["debug"]["TITLE_TAG"]
        assert "match" in result["debug"]["TITLE_TAG"]
        assert result["debug"]["TITLE_TAG"]["match"] is not None
        assert result["debug"]["H1_TITLE"]["match"] is not None
