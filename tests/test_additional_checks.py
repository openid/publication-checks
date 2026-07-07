"""Unit tests for content validation functions in spec_validator."""

import os
import sys

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_TESTS_DIR, ".."))

import spec_validator


class TestHistoryReferencesDraft:
    def test_history_contains_draft(self):
        history = {"history_present": True, "history": ["-01", "-01: Initial"]}
        assert spec_validator.history_references_draft(history, "01") is True

    def test_history_missing_draft(self):
        history = {"history_present": True, "history": ["-01", "-01: Initial"]}
        assert spec_validator.history_references_draft(history, "02") is False

    def test_no_history_entries(self):
        history = {"history_present": True, "history": []}
        assert spec_validator.history_references_draft(history, "01") is True


class TestCheckIetfIpr:
    def test_clean(self):
        assert spec_validator.check_ietf_ipr("<html>clean content</html>") == []

    def test_ietf_trust(self):
        assert "IETF Trust" in spec_validator.check_ietf_ipr("text with IETF Trust here")

    def test_bcp78(self):
        assert "BCP 78" in spec_validator.check_ietf_ipr("subject to BCP 78")


class TestCheckDraftDisclaimer:
    def test_present(self):
        assert spec_validator.check_draft_disclaimer("This document is not an OIDF International Standard") is True

    def test_absent(self):
        assert spec_validator.check_draft_disclaimer("<html>clean</html>") is False


class TestCheckOidcUsage:
    def test_clean(self):
        assert spec_validator.check_oidc_usage("<html>Uses OpenID Connect throughout</html>") == []

    def test_prose_occurrence(self):
        assert spec_validator.check_oidc_usage("This spec builds on OIDC concepts.") == [1]

    def test_citation_label(self):
        assert spec_validator.check_oidc_usage("as defined in [OIDC] Section 3") == [1]

    def test_lowercase_not_matched(self):
        assert spec_validator.check_oidc_usage('<a href="https://example.com/oidc/callback">') == []

    def test_embedded_word_not_matched(self):
        assert spec_validator.check_oidc_usage("OIDC4VP and XOIDC are other things") == []

    def test_multiple_lines(self):
        content = "line one OIDC\nclean line\n[OIDC] again\n"
        assert spec_validator.check_oidc_usage(content) == [1, 3]


class TestCheckNoncanonicalRefs:
    def test_clean(self):
        assert spec_validator.check_noncanonical_refs('<a href="https://openid.net/specs/foo.html">') == []

    def test_github_io(self):
        urls = spec_validator.check_noncanonical_refs('<a href="https://openid.github.io/foo/bar.html">')
        assert len(urls) == 1

    def test_bitbucket_io(self):
        urls = spec_validator.check_noncanonical_refs('<a href="https://openid.bitbucket.io/fapi/spec.html">')
        assert len(urls) == 1


class TestCheckMdIncludes:
    def test_xml2rfc_include(self):
        assert spec_validator.check_md_includes("<{{examples/file.json}}") is True

    def test_no_includes(self):
        assert spec_validator.check_md_includes("# Simple spec\nNo includes") is False

    def test_citation_not_flagged(self):
        assert spec_validator.check_md_includes("See {{RFC6749}} for details") is False
