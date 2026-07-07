import responses
import requests

import spec_validator


class TestContentRef:
    """Tests for content_ref(content, check_url=False, debug=False)."""

    def test_extract_references_dt_dd_format(self, draft_html):
        """The draft_html fixture has one reference to RFC2119 in dt/dd format."""
        result = spec_validator.content_ref(draft_html)
        assert len(result["references"]) == 1
        ref_id, ref_url = result["references"][0]
        assert ref_id == "RFC2119"
        assert ref_url == "https://www.rfc-editor.org/rfc/rfc2119"

    def test_empty_references_when_no_refs(self, malformed_html):
        """malformed_html has include_all_sections=False, so no references."""
        result = spec_validator.content_ref(malformed_html)
        assert result["references"] == []

    def test_check_url_false_returns_none_for_all_accessible(self, draft_html):
        """When check_url=False, all_accessible should be None."""
        result = spec_validator.content_ref(draft_html, check_url=False)
        assert result["all_accessible"] is None
        assert result["inaccessible_urls"] is None
        assert result["unverified_urls"] is None

    @responses.activate
    def test_check_url_true_accessible(self, draft_html):
        """Mock HEAD returning 200 -- all_accessible should be True."""
        responses.add(
            responses.HEAD,
            "https://www.rfc-editor.org/rfc/rfc2119",
            status=200,
        )
        result = spec_validator.content_ref(draft_html, check_url=True)
        assert result["all_accessible"] is True
        # Each reference tuple should have 3 elements when check_url=True
        assert len(result["references"][0]) == 3
        ref_id, ref_url, is_accessible = result["references"][0]
        assert ref_id == "RFC2119"
        assert is_accessible is True

    @responses.activate
    def test_check_url_head_fails_get_succeeds(self, draft_html):
        """HEAD returns 405 but GET returns 200 -- should be accessible (GET fallback)."""
        responses.add(
            responses.HEAD,
            "https://www.rfc-editor.org/rfc/rfc2119",
            status=405,
        )
        responses.add(
            responses.GET,
            "https://www.rfc-editor.org/rfc/rfc2119",
            status=200,
        )
        result = spec_validator.content_ref(draft_html, check_url=True)
        assert result["all_accessible"] is True

    @responses.activate
    def test_check_url_both_fail(self, draft_html):
        """Both HEAD and GET return 404 -- not accessible."""
        responses.add(
            responses.HEAD,
            "https://www.rfc-editor.org/rfc/rfc2119",
            status=404,
        )
        responses.add(
            responses.GET,
            "https://www.rfc-editor.org/rfc/rfc2119",
            status=404,
        )
        result = spec_validator.content_ref(draft_html, check_url=True)
        assert result["all_accessible"] is False

    @responses.activate
    def test_check_url_head_non_200_triggers_get(self, draft_html):
        """HEAD returns 301 -- not accepted, falls back to GET."""
        responses.add(
            responses.HEAD,
            "https://www.rfc-editor.org/rfc/rfc2119",
            status=301,
        )
        responses.add(
            responses.GET,
            "https://www.rfc-editor.org/rfc/rfc2119",
            status=200,
        )
        result = spec_validator.content_ref(draft_html, check_url=True)
        assert result["all_accessible"] is True

    @responses.activate
    def test_check_url_true_timeout(self, draft_html):
        """Mock HEAD raising a timeout -- all_accessible should be False."""
        responses.add(
            responses.HEAD,
            "https://www.rfc-editor.org/rfc/rfc2119",
            body=requests.exceptions.Timeout("Connection timed out"),
        )
        result = spec_validator.content_ref(draft_html, check_url=True)
        assert result["all_accessible"] is False

    @responses.activate
    def test_blocked_url_with_archive_snapshot_passes(self, draft_html):
        """HEAD and GET return 403 (bot protection) but the Internet Archive has a
        snapshot -- treated as accessible."""
        responses.add(
            responses.HEAD,
            "https://www.rfc-editor.org/rfc/rfc2119",
            status=403,
        )
        responses.add(
            responses.GET,
            "https://www.rfc-editor.org/rfc/rfc2119",
            status=403,
        )
        responses.add(
            responses.GET,
            "https://web.archive.org/web/2/https://www.rfc-editor.org/rfc/rfc2119",
            status=302,
            headers={"Location": "https://web.archive.org/web/20260630151745/https://www.rfc-editor.org/rfc/rfc2119"},
        )
        result = spec_validator.content_ref(draft_html, check_url=True)
        assert result["all_accessible"] is True
        assert result["inaccessible_urls"] == []
        assert result["unverified_urls"] == []
        assert result["references"][0][2] is True

    @responses.activate
    def test_blocked_url_no_archive_snapshot_fails(self, draft_html):
        """HEAD and GET return 403 and the Internet Archive has no snapshot --
        genuinely inaccessible."""
        responses.add(
            responses.HEAD,
            "https://www.rfc-editor.org/rfc/rfc2119",
            status=403,
        )
        responses.add(
            responses.GET,
            "https://www.rfc-editor.org/rfc/rfc2119",
            status=403,
        )
        responses.add(
            responses.GET,
            "https://web.archive.org/web/2/https://www.rfc-editor.org/rfc/rfc2119",
            status=404,
        )
        result = spec_validator.content_ref(draft_html, check_url=True)
        assert result["all_accessible"] is False
        assert result["inaccessible_urls"] == ["https://www.rfc-editor.org/rfc/rfc2119"]
        assert result["unverified_urls"] == []
        assert result["references"][0][2] is False

    @responses.activate
    def test_blocked_url_archive_unreachable_is_unverified(self, draft_html):
        """HEAD and GET return 403 and the Internet Archive is unreachable --
        unverified: does not fail the check, reported separately."""
        responses.add(
            responses.HEAD,
            "https://www.rfc-editor.org/rfc/rfc2119",
            status=403,
        )
        responses.add(
            responses.GET,
            "https://www.rfc-editor.org/rfc/rfc2119",
            status=403,
        )
        responses.add(
            responses.GET,
            "https://web.archive.org/web/2/https://www.rfc-editor.org/rfc/rfc2119",
            body=requests.exceptions.ConnectionError("archive.org unreachable"),
        )
        result = spec_validator.content_ref(draft_html, check_url=True)
        assert result["all_accessible"] is True
        assert result["inaccessible_urls"] == []
        assert result["unverified_urls"] == ["https://www.rfc-editor.org/rfc/rfc2119"]
        assert result["references"][0][2] is True

    @responses.activate
    def test_rate_limited_url_triggers_archive_fallback(self, draft_html):
        """HEAD and GET return 429 (rate limited) -- same archive fallback as 403."""
        responses.add(
            responses.HEAD,
            "https://www.rfc-editor.org/rfc/rfc2119",
            status=429,
        )
        responses.add(
            responses.GET,
            "https://www.rfc-editor.org/rfc/rfc2119",
            status=429,
        )
        responses.add(
            responses.GET,
            "https://web.archive.org/web/2/https://www.rfc-editor.org/rfc/rfc2119",
            status=302,
            headers={"Location": "https://web.archive.org/web/20260630151745/https://www.rfc-editor.org/rfc/rfc2119"},
        )
        result = spec_validator.content_ref(draft_html, check_url=True)
        assert result["all_accessible"] is True
        assert result["inaccessible_urls"] == []
