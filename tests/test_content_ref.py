import importlib
import responses
import requests

cli_tool = importlib.import_module("cli-tool")


class TestContentRef:
    """Tests for content_ref(content, check_url=False, debug=False)."""

    def test_extract_references_dt_dd_format(self, draft_html):
        """The draft_html fixture has one reference to RFC2119 in dt/dd format."""
        result = cli_tool.content_ref(draft_html)
        assert len(result["references"]) == 1
        ref_id, ref_url = result["references"][0]
        assert ref_id == "RFC2119"
        assert ref_url == "https://www.rfc-editor.org/rfc/rfc2119"

    def test_empty_references_when_no_refs(self, malformed_html):
        """malformed_html has include_all_sections=False, so no references."""
        result = cli_tool.content_ref(malformed_html)
        assert result["references"] == []

    def test_check_url_false_returns_none_for_all_accessible(self, draft_html):
        """When check_url=False, all_accessible should be None."""
        result = cli_tool.content_ref(draft_html, check_url=False)
        assert result["all_accessible"] is None

    @responses.activate
    def test_check_url_true_accessible(self, draft_html):
        """Mock HEAD returning 200 -- all_accessible should be True."""
        responses.add(
            responses.HEAD,
            "https://www.rfc-editor.org/rfc/rfc2119",
            status=200,
        )
        result = cli_tool.content_ref(draft_html, check_url=True)
        assert result["all_accessible"] is True
        # Each reference tuple should have 3 elements when check_url=True
        assert len(result["references"][0]) == 3
        ref_id, ref_url, is_accessible = result["references"][0]
        assert ref_id == "RFC2119"
        assert is_accessible is True

    @responses.activate
    def test_check_url_true_not_accessible(self, draft_html):
        """Mock HEAD returning 404 -- all_accessible should be False."""
        responses.add(
            responses.HEAD,
            "https://www.rfc-editor.org/rfc/rfc2119",
            status=404,
        )
        result = cli_tool.content_ref(draft_html, check_url=True)
        assert result["all_accessible"] is False
        _, _, is_accessible = result["references"][0]
        assert is_accessible is False

    @responses.activate
    def test_check_url_true_timeout(self, draft_html):
        """Mock HEAD raising a timeout -- all_accessible should be False."""
        responses.add(
            responses.HEAD,
            "https://www.rfc-editor.org/rfc/rfc2119",
            body=requests.exceptions.Timeout("Connection timed out"),
        )
        result = cli_tool.content_ref(draft_html, check_url=True)
        assert result["all_accessible"] is False
        _, _, is_accessible = result["references"][0]
        assert is_accessible is False
