"""End-to-end tests for the editor-facing wording of process.py output.

Motivated by openid/publication#207, where the PR comment blamed the author
for sections that were present, hid the actionable detail in log-only lines,
and dumped ~250 self-link URLs into one warning.
"""

import os
import re
import sys

import pytest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)
sys.path.insert(0, os.path.join(_TESTS_DIR, ".."))

from conftest import FIXTURES_DIR, _build_spec_html  # noqa: E402
from e2e_helpers import (  # noqa: E402
    create_test_repo, fail_lines, run_python_script, strip_ansi, today_str, warn_lines,
)

pytestmark = pytest.mark.e2e

_EMPTY_CSV = "Filename,Date,Size\n"


def _run_draft(tmp_path, html, filename="connect/openid-connect-test-1_0-01.html", env=None):
    spec_files = {
        filename: html,
        filename[:-5] + ".md": "# Spec\n",
    }
    repo_path, scripts_path = create_test_repo(tmp_path, spec_files, spec_list_csv_content=_EMPTY_CSV)
    result = run_python_script("process.py", repo_path, scripts_path, env_overrides=env)
    return result.returncode, strip_ansi(result.stdout)


# ---------------------------------------------------------------------------
# Regression: the real PR #207 HTML with absolute self-links
# ---------------------------------------------------------------------------

def test_pr207_absolute_self_links(tmp_path):
    with open(os.path.join(FIXTURES_DIR, "ipsie-al-scim-profile-1_0-00-absolute-links.html"), encoding="utf-8") as f:
        html = f.read()
    rc, out = _run_draft(
        tmp_path, html,
        filename="ipsie/ipsie-al-scim-profile-1_0-00.html",
        env={"OVERRIDE_TODAY": "2026-09-08"},
    )
    fails = fail_lines(out)
    warns = warn_lines(out)

    # The sections ARE present; the checker must not claim otherwise.
    assert not any("Document History section" in l for l in fails), fails
    assert not any("Notices section heading" in l for l in fails), fails
    assert not any("Missing sections" in l for l in fails), fails

    # One clear message about the self-links, naming the base URL and count.
    self_link = [l for l in fails if "its own editor's draft" in l]
    assert len(self_link) == 1, fails
    assert "https://openid.github.io/ipsie-scim-al/draft-openid-ipsie-al-scim-profile.html" in self_link[0]
    assert re.search(r", \d+ links\)", self_link[0])

    # The self-links must not also be dumped into the editor's-draft warning.
    # (The fixture's header links to the editor's-draft .xml source, which is
    # a genuine external reference and may still be warned about, once.)
    ref_warns = [l for l in warns if "references editor's draft" in l]
    assert len(ref_warns) <= 1, warns
    for l in ref_warns:
        assert "draft-openid-ipsie-al-scim-profile.html" not in l, l
        assert l.count("openid.github.io") == 1, l

    # The things that really are wrong with that revision are reported.
    assert any("IETF" in l for l in fails), fails
    assert any("Copyright year" in l and "2025" in l and "2026" in l for l in fails), fails
    assert rc == 1


# ---------------------------------------------------------------------------
# IETF boilerplate is a FAIL for drafts too
# ---------------------------------------------------------------------------

def test_ietf_boilerplate_fails_a_draft(tmp_path):
    today = today_str()
    html = _build_spec_html(title="OpenID Connect Test 1.0 - Draft 01", date=today, year=today[:4])
    html = html.replace("This is the abstract", "This is the abstract. Subject to BCP 78 and the IETF Trust")
    rc, out = _run_draft(tmp_path, html)
    assert rc == 1
    ietf = [l for l in fail_lines(out) if "IETF" in l]
    assert len(ietf) == 1, out
    assert 'ipr = "none"' in ietf[0]
    assert "seriesInfo" in ietf[0]
    assert not any("IETF" in l for l in warn_lines(out))


# ---------------------------------------------------------------------------
# Copyright year vs publication date
# ---------------------------------------------------------------------------

def test_copyright_year_mismatch_fails(tmp_path):
    today = today_str()
    last_year = str(int(today[:4]) - 1)
    html = _build_spec_html(title="OpenID Connect Test 1.0 - Draft 01", date=today, year=last_year)
    rc, out = _run_draft(tmp_path, html)
    assert rc == 1
    line = [l for l in fail_lines(out) if "Copyright year" in l]
    assert len(line) == 1, out
    assert last_year in line[0] and today in line[0]


def test_copyright_year_match_passes(tmp_path):
    today = today_str()
    html = _build_spec_html(title="OpenID Connect Test 1.0 - Draft 01", date=today, year=today[:4])
    rc, out = _run_draft(tmp_path, html)
    assert rc == 0, out
    assert not any("Copyright year" in l for l in fail_lines(out))


# ---------------------------------------------------------------------------
# Notices: say which part is wrong
# ---------------------------------------------------------------------------

def test_notices_heading_missing_is_distinct(tmp_path):
    today = today_str()
    html = _build_spec_html(title="OpenID Connect Test 1.0 - Draft 01", date=today, year=today[:4])
    html = html.replace('<a href="#name-notices" class="section-name selfRef">Notices</a>', "<h2>Legal stuff</h2>")
    rc, out = _run_draft(tmp_path, html)
    assert rc == 1
    line = [l for l in fail_lines(out) if "Notices" in l]
    assert len(line) == 1, out
    assert "heading" in line[0]
    assert "incomplete" not in line[0]


def test_notices_missing_phrase_is_named(tmp_path):
    today = today_str()
    html = _build_spec_html(title="OpenID Connect Test 1.0 - Draft 01", date=today, year=today[:4])
    html = html.replace("found at openid.net", "found somewhere")
    rc, out = _run_draft(tmp_path, html)
    assert rc == 1
    line = [l for l in fail_lines(out) if "Notices" in l]
    assert len(line) == 1, out
    assert "found at openid.net" in line[0]
    assert "heading" not in line[0]


# ---------------------------------------------------------------------------
# Workgroup: accepted values in the FAIL line itself
# ---------------------------------------------------------------------------

def test_workgroup_fail_line_lists_accepted_values(tmp_path):
    today = today_str()
    html = _build_spec_html(title="OpenID Connect Test 1.0 - Draft 01", date=today, year=today[:4], workgroup="IPSIE")
    rc, out = _run_draft(tmp_path, html, filename="ipsie/ipsie-test-1_0-01.html")
    line = [l for l in fail_lines(out) if "workgroup" in l.lower()]
    assert len(line) == 1, out
    assert "'IPSIE'" in line[0]
    assert "IPSIE Working Group" in line[0]


# ---------------------------------------------------------------------------
# Structure: display names, plain-English description, regex kept
# ---------------------------------------------------------------------------

def test_structure_failure_is_human_readable(tmp_path):
    today = today_str()
    html = _build_spec_html(title="OpenID Connect Test 1.0 - Draft 01", date=today, year=today[:4])
    html = html.replace(">Acknowledgements</a>", ">Thanks</a>")
    rc, out = _run_draft(tmp_path, html)
    assert rc == 1
    line = [l for l in fail_lines(out) if "structure" in l]
    assert len(line) == 1, out
    assert "Acknowledgements" in line[0]
    assert "ACKNOWLEDGEMENTS" not in line[0]
    # Human description first, regex still available on the following line.
    assert "'Acknowledgements' or 'Acknowledgments'" in out
    assert "regex:" in out


# ---------------------------------------------------------------------------
# Title has no draft number: one failure, with the actual title in it
# ---------------------------------------------------------------------------

def test_title_without_draft_number(tmp_path):
    today = today_str()
    html = _build_spec_html(title="OpenID Connect Test 1.0", date=today, year=today[:4])
    rc, out = _run_draft(tmp_path, html)
    assert rc == 1
    fails = fail_lines(out)
    assert not any("RELEASED" in l for l in fails), fails
    assert not any("spec-1_0-05.html" in l for l in fails), fails
    state_line = [l for l in fails if "Cannot tell" in l]
    assert len(state_line) == 1, fails
    assert "'OpenID Connect Test 1.0'" in state_line[0]
    assert "Draft 01" in state_line[0]
    assert "connect/openid-connect-test-1_0-01.html" in state_line[0]
    # The filename-mismatch check must not pile on a second failure for the same cause.
    assert not any("does not match filename" in l for l in fails), fails


def test_filename_mismatch_shows_actual_values(tmp_path):
    today = today_str()
    html = _build_spec_html(title="OpenID Connect Test 1.0 - Draft 02", date=today, year=today[:4])
    rc, out = _run_draft(tmp_path, html)
    assert rc == 1
    line = [l for l in fail_lines(out) if "does not match filename" in l]
    assert len(line) == 1, out
    assert "Draft 01" in line[0] and "Draft 02" in line[0]
    assert "spec-1_0-05.html" not in line[0]


# ---------------------------------------------------------------------------
# .zip warning when there is no markdown to inspect
# ---------------------------------------------------------------------------

def test_zip_warning_for_xml_only_source(tmp_path):
    today = today_str()
    html = _build_spec_html(title="OpenID Connect Test 1.0 - Draft 01", date=today, year=today[:4])
    spec_files = {
        "connect/openid-connect-test-1_0-01.html": html,
        "connect/openid-connect-test-1_0-01.xml": "<rfc/>\n",
    }
    repo_path, scripts_path = create_test_repo(tmp_path, spec_files, spec_list_csv_content=_EMPTY_CSV)
    result = run_python_script("process.py", repo_path, scripts_path)
    assert any(".zip" in l for l in warn_lines(result.stdout))


# ---------------------------------------------------------------------------
# Editor's-draft references: grouped, counted, capped
# ---------------------------------------------------------------------------

def test_editor_draft_reference_warning_is_grouped(tmp_path):
    today = today_str()
    html = _build_spec_html(title="OpenID Connect Test 1.0 - Draft 01", date=today, year=today[:4])
    links = "".join(
        f'<p><a href="https://openid.github.io/OpenID4VCI/spec.html#section-{i}">VCI {i}</a></p>'
        for i in range(1, 8)
    )
    html = html.replace("<p>This is the introduction.</p>", "<p>This is the introduction.</p>" + links)
    rc, out = _run_draft(tmp_path, html)
    line = [l for l in warn_lines(out) if "editor's draft" in l]
    assert len(line) == 1, out
    assert line[0].count("openid.github.io/OpenID4VCI/spec.html") == 1
    assert "7 links" in line[0]
    assert "#section-" not in line[0]
