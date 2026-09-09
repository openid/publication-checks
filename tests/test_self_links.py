"""Tests for self-link normalisation and the reworked non-canonical reference check.

Background: PR openid/publication#207 submitted HTML where every internal link
was an absolute editor's-draft URL (href="https://openid.github.io/x/spec.html#frag")
rather than href="#frag". That broke the Notices / Document History regexes and
produced a ~250-entry editor's-draft warning that was all self-links.
"""

import textwrap

import spec_validator

BASE = "https://openid.github.io/ipsie-scim-al/draft-openid-ipsie-al-scim-profile.html"


def _doc_with_absolute_self_links():
    return textwrap.dedent(f"""\
    <html><body>
    <h1 id="title">Spec</h1>
    <a href="{BASE}#" class="top">top</a>
    <h2 id="abstract"><a href="{BASE}#abstract">Abstract</a></h2>
    <dt id="RFC2119">[RFC2119]</dt>
    <dd><a href="https://www.rfc-editor.org/rfc/rfc2119">RFC 2119</a></dd>
    <p><a href="{BASE}#RFC2119">[RFC2119]</a></p>
    <section id="appendix-A">
      <h2 id="name-notices">
        <a href="{BASE}#appendix-A" class="section-number selfRef">Appendix A. </a><a href="{BASE}#name-notices" class="section-name selfRef">Notices</a>
      </h2>
    </section>
    <section id="appendix-B">
      <h2 id="name-document-history">
        <a href="{BASE}#appendix-B" class="section-number selfRef">Appendix B. </a><a href="{BASE}#name-document-history" class="section-name selfRef">Document History</a>
      </h2>
      <p>-00</p><ul><li>Initial draft</li></ul>
    </section>
    <p>See also <a href="https://openid.github.io/OpenID4VCI/openid-4-verifiable-credential-issuance-wg-draft.html#section-3">VCI</a>.</p>
    </body></html>
    """)


class TestNormaliseSelfLinks:
    def test_rewrites_self_links_to_fragments(self):
        content, _ = spec_validator.normalise_self_links(_doc_with_absolute_self_links())
        assert f'href="{BASE}#' not in content
        assert 'href="#name-notices"' in content
        assert 'href="#name-document-history"' in content
        assert 'href="#"' in content

    def test_reports_base_and_count(self):
        _, self_links = spec_validator.normalise_self_links(_doc_with_absolute_self_links())
        assert self_links == {BASE: 7}

    def test_leaves_links_to_other_editor_drafts_alone(self):
        content, _ = spec_validator.normalise_self_links(_doc_with_absolute_self_links())
        assert (
            'href="https://openid.github.io/OpenID4VCI/'
            'openid-4-verifiable-credential-issuance-wg-draft.html#section-3"'
        ) in content

    def test_no_self_links_is_a_no_op(self):
        html = '<a href="#abstract">x</a><a href="https://openid.github.io/foo/bar.html#s1">y</a>'
        assert spec_validator.normalise_self_links(html) == (html, {})

    def test_external_deep_links_are_not_treated_as_self_links(self):
        html = textwrap.dedent("""\
        <h1 id="title">Spec</h1>
        <a href="https://openid.github.io/other/spec.html#section-1">a</a>
        <a href="https://openid.github.io/other/spec.html#section-2">b</a>
        <a href="https://openid.github.io/other/spec.html#section-3">c</a>
        """)
        assert spec_validator.normalise_self_links(html) == (html, {})

    def test_external_link_to_a_shared_section_id_is_not_a_self_link(self):
        # Section ids such as name-introduction exist in almost every spec, so
        # a reference into another spec must not be mistaken for a self-link
        # just because this document happens to have the same id.
        html = textwrap.dedent("""\
        <h2 id="name-introduction"><a href="#name-introduction" class="section-name selfRef">Introduction</a></h2>
        <p>See <a href="https://openid.github.io/OpenID4VCI/spec.html#name-introduction">VCI</a>.</p>
        """)
        assert spec_validator.normalise_self_links(html) == (html, {})

    def test_section_checks_pass_after_normalisation(self):
        normalised, _ = spec_validator.normalise_self_links(_doc_with_absolute_self_links())
        assert spec_validator.content_notices(normalised)["notices"] is True
        assert spec_validator.content_history(normalised)["history_present"] is True


class TestCheckNoncanonicalRefsGrouped:
    def test_strips_fragments_and_counts(self):
        html = (
            '<a href="https://openid.github.io/OpenID4VCI/spec.html#section-1">a</a>'
            '<a href="https://openid.github.io/OpenID4VCI/spec.html#section-2">b</a>'
            '<a href="https://openid.github.io/OpenID4VCI/spec.html">c</a>'
            '<a href="https://openid.bitbucket.io/fapi/fapi-2_0.html#x">d</a>'
        )
        assert spec_validator.check_noncanonical_refs(html) == [
            ("https://openid.bitbucket.io/fapi/fapi-2_0.html", 1),
            ("https://openid.github.io/OpenID4VCI/spec.html", 3),
        ]

    def test_fragment_only_links_are_ignored(self):
        assert spec_validator.check_noncanonical_refs('<a href="#name-notices">x</a>') == []


class TestSectionDescriptions:
    def test_every_structural_section_has_a_description(self):
        for key in ["ABSTRACT", "INTRODUCTION", "REFERENCES", "NORMATIVE_REFERENCES",
                    "INFORMATIVE_REFERENCES", "ACKNOWLEDGEMENTS", "SECURITY"]:
            name, description = spec_validator.SECTION_DESCRIPTIONS[key]
            assert name and description
            assert key in spec_validator.PATTERNS

    def test_acknowledgements_mentions_both_spellings(self):
        _, description = spec_validator.SECTION_DESCRIPTIONS["ACKNOWLEDGEMENTS"]
        assert "Acknowledgements" in description and "Acknowledgments" in description


class TestContentNoticesMissingPhrases:
    def test_missing_phrases_always_returned(self, draft_html):
        result = spec_validator.content_notices(draft_html)
        assert result["missing_phrases"] == []

    def test_missing_phrases_lists_what_is_absent(self, draft_html):
        broken = draft_html.replace("found at openid.net", "found somewhere")
        result = spec_validator.content_notices(broken)
        assert result["license_text_present"] is False
        assert any("found at openid.net" in p for p in result["missing_phrases"])
