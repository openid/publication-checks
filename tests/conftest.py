import os
import sys
import pytest
import textwrap

# Add the repo root to the path so we can import spec_validator as a module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


def _oidf_notices_text(year):
    """Build the standard OIDF notices/license text for test fixtures."""
    return textwrap.dedent(f"""\
    <p>Copyright (c) {year} The OpenID Foundation</p>
    <p>The OpenID Foundation (OIDF) grants to any Contributor, developer, implementer,
    or other interested party a non-exclusive, royalty free, worldwide copyright license
    to reproduce, prepare derivative works from, distribute, perform and display, this
    Implementers Draft, Final Specification, or Final Specification Incorporating Errata
    Corrections solely for the purposes of
    (i) developing specifications, and (ii)
    implementing Implementers Drafts, Final Specifications,
    and Final Specification Incorporating Errata Corrections
    based on such documents, provided that attribution be made to the OIDF as the source
    of the material, but that such attribution does not indicate an endorsement by the OIDF.</p>
    <p>The technology described in this specification was made available from contributions
    from various sources, including
    members of the OpenID Foundation and others.
    Although the OpenID Foundation has taken steps to help ensure that the technology is
    available for distribution, it
    takes no position regarding the validity or scope of any intellectual property or other
    rights that might be claimed to pertain to the implementation or use of the technology
    described in this specification or
    the extent to which any license under such rights might or might not be available;
    neither does it represent that it has
    made any independent effort to identify any such rights.</p>
    <p>The OpenID Foundation and the contributors to this specification make no
    (and hereby expressly disclaim any)
    warranties (express, implied, or otherwise),
    including implied warranties of
    warranties of merchantability, non-infringement, fitness for a particular purpose,
    or title,
    related to this specification and the
    entire risk as to implementing this specification is assumed by the implementer.</p>
    <p>The OpenID Intellectual Property Rights policy requires contributors to offer a patent promise
    not to assert certain patent claims against other contributors
    and against implementers.
    The OpenID Foundation invites any interested party to bring to its attention any
    copyrights, patents, patent applications, or other proprietary rights
    that may cover technology that may be required to practice this specification.
    This policy can be found at openid.net.</p>
    <p>OpenID invites any interested party to bring to its attention any
    copyrights, patents, patent applications, or other proprietary rights
    that may cover technology that may be required to practice this specification.</p>
    """)


def _build_spec_html(title, state_suffix, year="2026", date="2026-03-20",
                     include_history=True, include_notices=True,
                     include_authors=True, include_all_sections=True,
                     author_format="div"):
    """Build a minimal but realistic OpenID spec HTML document for testing."""
    history_section = ""
    if include_history:
        history_section = textwrap.dedent("""\
        <section id="appendix-A">
          <h2 id="name-document-history">
            <a href="#appendix-A" class="section-number selfRef">Appendix A. </a><a href="#name-document-history" class="section-name selfRef">Document History</a>
          </h2>
          <p>-01</p>
          <ul><li>Initial draft</li></ul>
        </section>
        """)

    notices_section = ""
    if include_notices:
        notices_section = f"""\
        <a href="#name-notices" class="section-name selfRef">Notices</a>
        {_oidf_notices_text(year)}
        """

    authors_section = ""
    if include_authors:
        if author_format == "div":
            authors_section = textwrap.dedent("""\
            <dd class="authors">
              <div class="author">
                <div class="author-name">Jane Doe</div>
                <div class="org">Example Corp</div>
              </div>
              <div class="author">
                <div class="author-name">John Smith</div>
                <div class="org">Test Inc</div>
              </div>
            </dd>
            """)
        else:
            authors_section = textwrap.dedent("""\
            <table width="99%" border="0" cellpadding="0" cellspacing="0">
            <tbody>
            <tr><td class="author-text">&nbsp;</td><td class="author-text">Jane Doe</td></tr>
            <tr><td class="author-text">&nbsp;</td><td class="author-text">Example Corp</td></tr>
            <tr><td class="author-text">&nbsp;</td><td class="author-text">&nbsp;</td></tr>
            <tr><td class="author-text">&nbsp;</td><td class="author-text">&nbsp;</td></tr>
            <tr><td class="author-text">&nbsp;</td><td class="author-text">&nbsp;</td></tr>
            </tbody>
            </table>
            """)

    optional_sections = ""
    if include_all_sections:
        optional_sections = textwrap.dedent("""\
        <h2 id="name-introduction"><a href="#name-introduction" class="section-name selfRef">Introduction</a></h2>
        <p>This is the introduction.</p>
        <h2 id="name-references">2.&nbsp;<a href="#name-references" class="section-name selfRef">References</a></h2>
        <h3 id="name-normative-references"><a href="#name-normative-references" class="section-name selfRef">Normative References</a></h3>
        <dt id="RFC2119">[RFC2119]</dt>
        <dd><a href="https://www.rfc-editor.org/rfc/rfc2119">Key words for use in RFCs</a></dd>
        <h3 id="name-informative-references"><a href="#name-informative-references" class="section-name selfRef">Informative References</a></h3>
        <h2 id="name-security-considerations">3.&nbsp;<a href="#name-security-considerations" class="section-name selfRef">Security Considerations</a></h2>
        <p>Security considerations go here.</p>
        <h2 id="name-acknowledgements"><a href="#name-acknowledgements" class="section-name selfRef">Acknowledgements</a></h2>
        <p>Thanks to the contributors.</p>
        """)

    html = textwrap.dedent(f"""\
    <!DOCTYPE html>
    <html>
    <head>
    <title>{title}</title>
    </head>
    <body>
    <h1 id="title">{title}</h1>
    <dd class="published">
      <time datetime="{date}">{date}</time>
    </dd>
    {authors_section}
    <h2 id="abstract"><a href="#abstract">Abstract</a></h2>
    <p>This is the abstract of the specification.</p>
    {optional_sections}
    {history_section}
    {notices_section}
    </body>
    </html>
    """)
    return html


@pytest.fixture
def draft_html():
    return _build_spec_html(
        title="OpenID Connect Example 1.0 - Draft 01",
        state_suffix="draft",
        include_history=True,
    )


@pytest.fixture
def final_html():
    return _build_spec_html(
        title="Final: OpenID Connect Example 1.0",
        state_suffix="final",
        include_history=False,
    )


@pytest.fixture
def errata_html():
    return _build_spec_html(
        title="OpenID Connect Example 1.0 incorporating errata set 1",
        state_suffix="errata",
        include_history=False,
    )


@pytest.fixture
def implementors_html():
    return _build_spec_html(
        title="OpenID Connect Example 1.0 - Implementors Draft 1",
        state_suffix="implementors",
        include_history=True,
    )


@pytest.fixture
def malformed_html():
    return _build_spec_html(
        title="OpenID Connect Example 1.0 - Draft 01",
        state_suffix="draft",
        include_history=False,
        include_notices=False,
        include_authors=False,
        include_all_sections=False,
    )


@pytest.fixture
def no_history_html():
    return _build_spec_html(
        title="OpenID Connect Example 1.0 - Draft 01",
        state_suffix="draft",
        include_history=False,
    )


@pytest.fixture
def bad_notices_html():
    return _build_spec_html(
        title="OpenID Connect Example 1.0 - Draft 01",
        state_suffix="draft",
        include_history=True,
        include_notices=False,
    )


@pytest.fixture
def table_authors_html():
    return _build_spec_html(
        title="OpenID Connect Example 1.0 - Draft 01",
        state_suffix="draft",
        author_format="table",
    )


@pytest.fixture
def tmp_csv(tmp_path):
    """Create a temporary CSV file mimicking spec-list.csv."""
    csv_content = (
        "Filename,Date,Size\n"
        "openid-connect-core-1_0.html,2024-01-15,123K\n"
        "openid-connect-core-1_0-final.html,2024-01-15,123K\n"
        "openid-connect-core-1_0-errata1.html,2024-06-01,125K\n"
        "openid-connect-discovery-1_0-21.html,2023-11-08,45K\n"
    )
    csv_path = tmp_path / "spec-list.csv"
    csv_path.write_text(csv_content)
    return str(csv_path)


@pytest.fixture
def draft_html_file(tmp_path, draft_html):
    """Write draft HTML to a temp file and return the path."""
    p = tmp_path / "openid-connect-example-1_0-01.html"
    p.write_text(draft_html)
    return str(p)


@pytest.fixture
def final_html_file(tmp_path, final_html):
    """Write final HTML to a temp file and return the path."""
    p = tmp_path / "openid-connect-example-1_0-final.html"
    p.write_text(final_html)
    return str(p)


@pytest.fixture
def errata_html_file(tmp_path, errata_html):
    """Write errata HTML to a temp file and return the path."""
    p = tmp_path / "openid-connect-example-1_0-01.html"
    p.write_text(errata_html)
    return str(p)
