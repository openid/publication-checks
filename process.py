#!/usr/bin/env python3
"""Python replacement for process.sh – pre-publication validation.

Calls spec_validator functions directly instead of spawning
``python cli-tool.py`` as a subprocess.  The only subprocess call is
``git diff`` to discover changed HTML files.

Exit codes:
    0 – all checks passed
    1 – one or more checks failed
"""
from __future__ import annotations

import csv
import datetime
import os
import re
import subprocess
import sys

# ---------------------------------------------------------------------------
# Ensure spec_validator can be imported when this script lives in the same
# directory (e.g. the ``openid-workflow/`` scripts directory).
# ---------------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import spec_validator  # noqa: E402

# ---------------------------------------------------------------------------
# Colour helpers (ANSI escape codes, same palette as process.sh)
# ---------------------------------------------------------------------------
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
CYAN = "\033[0;36m"
NC = "\033[0m"

# ---------------------------------------------------------------------------
# Allowed workgroup metadata values per WG directory, seeded from the values
# used in already-published specs (issue publication#192). Compared
# case-insensitively. Regenerate the observed values with:
#   grep -h -o '<dd class="workgroup">[^<]*' sync/specs/*.html | sed 's/.*>//' | sort -u
# in the publication repo.
# ---------------------------------------------------------------------------
WG_WORKGROUP_NAMES = {
    "authzen": {"OpenID AuthZEN"},
    "connect": {"connect", "OpenID Connect", "OpenID Connect A/B",
                "OpenID Connect Working Group"},
    "dchp": {"Digital Credentials Harmonized Presentation"},
    "digital-credentials-protocols": {"Digital Credentials Protocols",
                                      "OpenID Digital Credentials Protocols"},
    "ekyc-ida": {"eKYC-IDA", "OpenID eKYC-IDA"},
    "fapi": {"fapi", "OpenID FAPI"},
    "igov": {"OpenID iGov Working Group", "OpenID Foundation iGov Working Group"},
    "ipsie": {"IPSIE Working Group"},
    "sharedsignals": {"Shared Signals", "Shared Signals and Events",
                      "Shared Signals and Events Working Group"},
}


def echo_error(msg: str) -> None:
    print(f"{RED}{msg}{NC}")


def echo_warn(msg: str) -> None:
    print(f"{YELLOW}{msg}{NC}")


def echo_good(msg: str) -> None:
    print(f"{GREEN}{msg}{NC}")


def echo_info(msg: str) -> None:
    print(f"{CYAN}{msg}{NC}")


def report_reference_results(file, ref_result):
    """Report the outcome of the reference URL check; returns True if the file fails.

    Inaccessible URLs are a failure. Unverified URLs (the site blocks automated
    requests and the Internet Archive could not be reached to confirm a
    snapshot) only produce a warning and do not block publication.
    """
    inaccessible = sorted(set(ref_result.get("inaccessible_urls") or []))
    unverified = sorted(set(ref_result.get("unverified_urls") or []))
    failed = ref_result.get("all_accessible") is False
    if failed:
        echo_error(f"FAIL: Problem with References in {file}. These referenced URLs are not accessible: {', '.join(inaccessible)}")
    if unverified:
        echo_warn(
            f"WARNING: Could not verify these referenced URLs in {file}: {', '.join(unverified)}. "
            "The site blocks automated requests (HTTP 403/429 or a 202 WAF challenge) and the Internet Archive could not be reached to confirm a snapshot. "
            "Please verify the links manually in a browser."
        )
    if not failed and not unverified:
        echo_good(f"PASS: References in {file} is good")
    return failed


def final_exists_in_csv(unversioned_name, csv_path):
    """Check whether a -final.html spec exists in the CSV for the given base name."""
    final_pattern = re.compile(re.escape(unversioned_name) + r"-final\.html")
    try:
        with open(csv_path, "r", newline="") as csvf:
            reader = csv.reader(csvf)
            for row in reader:
                if row and final_pattern.search(row[0]):
                    return True
    except FileNotFoundError:
        pass
    return False


def _n_links(count):
    return f"{count} link{'s' if count != 1 else ''}"


def _first_few(items, limit=5, sep=", "):
    """Join up to `limit` items, noting how many were left out."""
    shown = sep.join(items[:limit])
    if len(items) > limit:
        shown += f" (+{len(items) - limit} more)"
    return shown


def _show_history_diagnostic():
    """Print diagnostic info for missing Document History section."""
    echo_info(
        "  If the section is present, check its heading markup matches one of these formats:\n"
        "    - <section id=\"appendix-X\"><h2 id=\"name-document-history\">...Document History...</h2>\n"
        "    - <h1 id=\"...-document-history\">...Document History</h1>\n"
        "    - <h3>Appendix X.&nbsp; Document History</h3>\n"
        "  The heading must contain the text 'Document History'."
    )


def _check_history_references_draft(draft_num_match, history_result):
    """Return True (pass) if the history section references the current draft number."""
    if draft_num_match and history_result.get("history"):
        draft_num = draft_num_match.group(1)
        if spec_validator.history_references_draft(history_result, draft_num):
            echo_good(f"PASS: History section references draft {draft_num}")
            return True
        else:
            echo_error(
                f"FAIL: History section does not reference current draft number {draft_num}"
            )
            return False
    return True


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------
def main() -> int:
    debug = os.environ.get("DEBUG", "false").lower() == "true"

    # ---- Fetch spec-list.csv -------------------------------------------
    csv_path = os.path.join(_SCRIPT_DIR, "spec-list.csv")
    if os.path.isfile(csv_path) and os.environ.get("SKIP_CSV_FETCH"):
        print("Using existing spec-list.csv (SKIP_CSV_FETCH is set)")
    else:
        csv_data = spec_validator.get_spec_list_csv()
        if csv_data is None:
            echo_error("FAIL: Could not fetch spec list from openid.net. Check network connectivity and retry.")
            return 1
        with open(csv_path, "w", newline="") as f:
            f.write(csv_data)

    # ---- Get changed HTML files ------------------------------------------
    # Prefer CHANGED_FILES env var (newline-separated) if set, otherwise git diff
    changed_files_env = os.environ.get("CHANGED_FILES", "").strip()
    if changed_files_env:
        all_changed = changed_files_env.splitlines()
    else:
        try:
            result = subprocess.run(
                ["git", "-C", "../.", "diff", "--name-only", "origin/main...HEAD"],
                capture_output=True, text=True, check=True,
            )
            all_changed = result.stdout.strip().splitlines()
        except subprocess.CalledProcessError:
            all_changed = []

    changed_files = [f for f in all_changed if f.endswith(".html")]

    print(f"Number of new files detected: {CYAN}{len(changed_files)}{NC}")

    if debug:
        for f in changed_files:
            print(f)

    print("List of changed files detected: ")
    subdirectories: list[str] = []
    for file in changed_files:
        echo_info(file)
        subdirectories.append(os.path.dirname(file))

    # ---- No HTML files? ------------------------------------------------
    if not changed_files:
        echo_error("FAIL: No HTML files have changed.  Exiting script.")
        return 1

    # ---- Check only one WG sub-directory --------------------------------
    print(f"Sub-Directories: {len(set(subdirectories))}")
    unique_dirs = sorted(set(subdirectories))
    if len(unique_dirs) != 1:
        echo_error(
            "FAIL: More than one WG sub-directory updated in a single PR "
            f"({', '.join(unique_dirs)}). Please split into one PR per Working Group."
        )
        return 1

    # ---- Check WG directory is a known one --------------------------------
    # The known WG directories are the actual directories in the repo root,
    # excluding infrastructure directories. This way, adding a new WG just
    # requires creating the directory in the publication repo.
    repo_root = os.path.abspath(os.path.join(_SCRIPT_DIR, ".."))
    _INFRA_DIRS = {"sync", "to-publish"}
    # List directories on origin/main (not the working tree, which could
    # contain directories added by the PR branch to bypass the check).
    try:
        result = subprocess.run(
            ["git", "-C", repo_root, "ls-tree", "--name-only", "-d", "origin/main"],
            capture_output=True, text=True, check=True,
        )
        known_dirs = {
            d for d in result.stdout.strip().splitlines()
            if not d.startswith(".")
            and d not in _INFRA_DIRS
        }
    except subprocess.CalledProcessError:
        # Fallback to working tree if git command fails (e.g., in tests)
        known_dirs = {
            d for d in os.listdir(repo_root)
            if os.path.isdir(os.path.join(repo_root, d))
            and not d.startswith(".")
            and d not in _INFRA_DIRS
        }
    for wg_dir in unique_dirs:
        if wg_dir not in known_dirs:
            echo_error(
                f"FAIL: '{wg_dir}' is not a recognised Working Group directory. "
                f"Known directories: {', '.join(sorted(known_dirs))}"
            )
            return 1

    # ---- Reject unversioned HTML filenames ------------------------------
    # Unversioned files (e.g. foo-1_0.html) must only be produced by publish.py
    # when the PR is merged — users should always submit versioned files
    # (-NN, -final, -errataN, -IDN). Without this check, they fall through to
    # a misleading "source file missing" error (issue #175).
    unversioned = [
        f for f in changed_files
        if spec_validator.filename_state(os.path.basename(f))["state"] == "CURRENT"
    ]
    if unversioned:
        for f in unversioned:
            echo_error(
                f"FAIL: {f} is an unversioned filename. Do not submit unversioned "
                "HTML files — they are produced automatically from the versioned "
                "file when the PR is merged. Submit a versioned filename with a "
                "-NN (draft), -final, -errataN, or -IDN suffix."
            )
        return 1

    # ---- Process each changed HTML file ---------------------------------
    any_fails = False

    for file in changed_files:
        doc_fails = False
        print("-" * 114)
        print(f"Processing file: {file}")

        file_path = os.path.join("..", file)
        base_html = os.path.basename(file)
        stem = os.path.splitext(file)[0]  # e.g. connect/openid-connect-test-1_0-01
        draft_num_match = re.search(r'-(\d{1,2})\.html$', base_html)

        print("Checking source files")
        # -- Source-file checks -------------------------------------------
        zip_path = os.path.join("..", f"{stem}.zip")
        md_path = os.path.join("..", f"{stem}.md")
        xml_path = os.path.join("..", f"{stem}.xml")

        if not os.path.isfile(zip_path):
            # If md source exists and references external files, zip is required
            has_includes = False
            if os.path.isfile(md_path):
                try:
                    with open(md_path, "r", encoding="utf-8") as mdf:
                        md_content = mdf.read()
                    has_includes = spec_validator.check_md_includes(md_content)
                except (FileNotFoundError, UnicodeDecodeError):
                    pass
            if has_includes:
                echo_error(
                    f"FAIL: {stem}.md references external files but no .zip archive "
                    f"is provided. A .zip containing all source files is required."
                )
                doc_fails = True
            elif not os.path.isfile(md_path):
                echo_warn(
                    f"WARNING: No .zip file for {stem}. If the source is split across "
                    "several files, a .zip containing all of them is required."
                )

        if not os.path.isfile(md_path) and not os.path.isfile(xml_path):
            echo_error(
                f"FAIL: Either Markdown or XML Source is required. "
                f"Either a file called {stem}.md or called {stem}.xml is required."
            )
            doc_fails = True

        print("Checking companion files")
        # -- Check companion files match previous version -------------------
        if draft_num_match:
            draft_num_pre = int(draft_num_match.group(1))
            if draft_num_pre > 1:
                # Derive previous draft stem from current basename: replace trailing digits
                base_stem = os.path.splitext(base_html)[0]
                prev_stem = re.sub(r'-\d{1,2}$', f"-{draft_num_pre - 1:02d}", base_stem)
                try:
                    with open(csv_path, "r", newline="") as csvf:
                        csv_content = csvf.read()
                    prev_extensions = set()
                    for ext in ("html", "md", "xml", "zip", "txt"):
                        if f"{prev_stem}.{ext}" in csv_content:
                            prev_extensions.add(ext)
                    if prev_extensions:
                        current_extensions = set()
                        for ext in ("html", "md", "xml", "zip", "txt"):
                            check_path = os.path.join("..", f"{stem}.{ext}")
                            if ext == "html" or os.path.isfile(check_path):
                                current_extensions.add(ext)
                        missing = prev_extensions - current_extensions
                        if missing:
                            echo_error(
                                f"FAIL: Previous version {prev_stem} included "
                                f"{', '.join(f'.{e}' for e in sorted(missing))} "
                                f"but this submission does not"
                            )
                            doc_fails = True
                        else:
                            echo_good("PASS: Companion files match previous version")
                except FileNotFoundError:
                    pass

        print("Checking for duplicate filename")
        # -- Duplicate check (check-draft) --------------------------------
        exit_code = spec_validator.check_draft_in_csv(base_html, csv_path)
        if exit_code != spec_validator.EXIT_SUCCESS:
            echo_error(f"FAIL: File {file} already exists.")
            doc_fails = True
        else:
            echo_good(f"PASS: {file} does not already exist")

        # -- Read file content once ----------------------------------------
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                content = fh.read()
        except (FileNotFoundError, PermissionError) as exc:
            echo_error(f"FAIL: Cannot read {file}: {exc}. Check the file exists and has correct permissions.")
            doc_fails = True
            any_fails = True
            print("-" * 114)
            print("-" * 114)
            continue

        print("Checking internal links")
        # -- Absolute links to the document's own editor's draft -----------
        # Some toolchains emit every internal link as an absolute URL on
        # openid.github.io. Rewrite them to #fragment links so the section
        # checks below see the document as a reader would, and fail the
        # submission because a published spec must not link out to the
        # editor's draft (issue seen in publication#207).
        content, self_links = spec_validator.normalise_self_links(content)
        if self_links:
            for base_url, count in sorted(self_links.items()):
                echo_error(
                    f"FAIL: Internal links in {file} point to its own editor's draft "
                    f"({base_url}, {_n_links(count)}). The table of contents and cross "
                    "references must link within the document (href=\"#section\"), "
                    "otherwise readers of the published spec are sent to the editor's "
                    "draft. Regenerate the HTML without an absolute base URL."
                )
            doc_fails = True
        else:
            echo_good(f"PASS: Internal links in {file} stay within the document")

        print("Checking document history")
        # -- History section -----------------------------------------------
        history_result = spec_validator.content_history(content, debug)
        has_history = history_result["history_present"]

        print("Checking document state")
        # -- Document state ------------------------------------------------
        state_result = spec_validator.content_state(content, debug)
        state = state_result["state"]

        # IMPLEMENTERS filenames (-ID1.html) use a standard DRAFT title,
        # so content_state returns DRAFT.  Use the filename to override.
        fn_state = spec_validator.filename_state(base_html)
        if fn_state["state"] == "IMPLEMENTERS" and state == "DRAFT":
            state = "IMPLEMENTERS"

        # Print state info similar to shell (the shell calls run_cli_tool which
        # prints the cli-tool output for -content-state and -content-history).
        print(f"Content State:")
        for k, v in state_result.items():
            if k != "debug":
                print(f"  {k}: {v}")

        print(f"Document History:")
        print(f"  history_present: {history_result['history_present']}")
        if history_result.get("history"):
            entries = history_result["history"]
            preview = "; ".join(str(e) for e in entries[:5])
            if len(preview) > 80:
                preview = preview[:80] + "..."
            if len(entries) > 5:
                preview += f" (+{len(entries) - 5} more)"
            print(f"  entries: {preview}")

        # Derive versioned / unversioned names (same logic as shell)
        versioned_name = os.path.splitext(os.path.basename(file))[0]
        # Strip state-specific suffixes to get the base spec name:
        #   -01 (draft), -final, -errata1, -ID2
        unversioned_name = re.sub(
            r'(?:-\d{1,2}|-final|-errata\d+|-ID\d+)$', '', versioned_name,
        )

        title_result = spec_validator.content_title(content, debug)
        found_title = title_result["title_tag"] or "(no <title> found)"
        # True once the state block below has reported that the state could
        # not be determined, so later checks do not pile on for the same cause.
        state_unknown = False

        print("Checking state and history consistency")
        # -- State / history consistency -----------------------------------
        if state == "UNKNOWN":
            echo_error(f"FAIL: Problem with document titles in {file} so state is UNKNOWN")
            # Show what was found to help diagnose
            echo_info(f"  <title>: {title_result['title_tag'][:100] if title_result['title_tag'] else 'not found'}")
            echo_info(f"  <h1>: {title_result['h1_title'][:100] if title_result['h1_title'] else 'not found'}")
            doc_fails = True
            state_unknown = True
        elif state == "DRAFT":
            echo_good("Document is in DRAFT state")
            if has_history:
                echo_good("PASS: Document has a history section")
                if not _check_history_references_draft(draft_num_match, history_result):
                    doc_fails = True
            else:
                echo_error(f"FAIL: {file} is a draft but does not have a Document History section. Drafts require a history section listing changes.")
                _show_history_diagnostic()
                doc_fails = True

            # Check sequential draft numbering
            if draft_num_match:
                draft_num = int(draft_num_match.group(1))
                if draft_num >= 0:
                    prev_draft = f"{unversioned_name}-{draft_num - 1:02d}.html"
                    try:
                        with open(csv_path, "r", newline="") as csvf:
                            csv_content = csvf.read()
                        if draft_num == 0 or prev_draft in csv_content:
                            echo_good(f"PASS: Draft numbering is sequential")
                        else:
                            echo_warn(
                                f"WARNING: Previous draft {prev_draft} not found in published specs. "
                                f"Draft numbers should be sequential."
                            )
                    except FileNotFoundError:
                        pass

            # Check that no final already exists for this spec
            if final_exists_in_csv(unversioned_name, csv_path):
                echo_error(
                    f"FAIL: {file} is a draft but a Final spec already exists on openid.net. "
                    "Post-final drafts must include errata language in the title, e.g. "
                    "'Spec Name 1.0 - Draft NN incorporating errata set N'"
                )
                doc_fails = True
        elif state == "FINAL":
            echo_good("Document is in FINAL state")
            if not has_history:
                echo_good("PASS: Document does not have a history section")
            else:
                echo_error(f"FAIL: {file} is a Final spec but contains a Document History section. Remove the history section before publishing as Final.")
                doc_fails = True
        elif state == "IMPLEMENTERS":
            echo_good("Document is in IMPLEMENTERS state")
            if has_history:
                echo_good("PASS: Document has a history section")
            else:
                echo_error(f"FAIL: {file} is an Implementers Draft but does not have a Document History section. Drafts require a history section listing changes.")
                _show_history_diagnostic()
                doc_fails = True

            # An Implementers Draft cannot follow a Final: post-final
            # changes must be published as errata.
            if final_exists_in_csv(unversioned_name, csv_path):
                echo_error(
                    f"FAIL: {file} is an Implementers Draft but a Final spec already exists "
                    "on openid.net. Post-final changes must include errata language in the "
                    "title, e.g. 'Spec Name 1.0 - Draft NN incorporating errata set N'"
                )
                doc_fails = True

            # Check sequential Implementers Draft numbering. Warning only:
            # for many published specs the early IDs are not present under
            # -IDN naming on openid.net.
            id_num_match = re.search(r'-ID(\d+)\.html$', base_html)
            if id_num_match:
                id_num = int(id_num_match.group(1))
                if id_num > 1:
                    prev_id = f"{unversioned_name}-ID{id_num - 1}.html"
                    try:
                        with open(csv_path, "r", newline="") as csvf:
                            csv_content = csvf.read()
                        if prev_id in csv_content:
                            echo_good("PASS: Implementers Draft numbering is sequential")
                        else:
                            echo_warn(
                                f"WARNING: Previous Implementers Draft {prev_id} not found in published specs. "
                                "Implementers Draft numbers should be sequential."
                            )
                    except FileNotFoundError:
                        pass
        elif state in ("ERRATA", "DRAFT_ERRATA"):
            echo_good(f"Document is in {state} state")

            if state == "DRAFT_ERRATA":
                # Draft errata (pre-vote) requires history, like DRAFT
                if has_history:
                    echo_good("PASS: Document has a history section")
                    if not _check_history_references_draft(draft_num_match, history_result):
                        doc_fails = True
                else:
                    echo_error(f"FAIL: {file} has 'errata' in the title and is a draft, but does not have a Document History section. Draft errata specs require a history section listing changes.")
                    _show_history_diagnostic()
                    doc_fails = True
            else:
                # Approved errata (post-vote) must not have history
                if not has_history:
                    echo_good("PASS: Document does not have a history section")
                else:
                    echo_error(f"FAIL: {file} is an approved errata but contains a Document History section. Remove the history section before publishing.")
                    doc_fails = True

                # Approved errata are published as Final Specifications
                # Incorporating Errata Corrections, so like -final specs the
                # header must indicate Status: Final.
                if re.search(spec_validator.PATTERNS['FINAL_CONTENT'], content, re.IGNORECASE | re.DOTALL):
                    echo_good("PASS: Document header contains 'Status: Final'")
                else:
                    echo_error(
                        f"FAIL: {file} is an approved errata but the document header "
                        f"does not contain 'Status: Final'. Add <dd class=\"status\">Final</dd> or "
                        f"<td class=\"header\">Final</td> to the document header."
                    )
                    doc_fails = True

                # Check sequential errata set numbering. Unlike draft
                # numbers (where a skipped number only warns), errata sets
                # are never skipped, so this is a hard failure.
                errata_num_match = re.search(r'-errata(\d+)\.html$', base_html)
                if errata_num_match:
                    errata_num = int(errata_num_match.group(1))
                    if errata_num > 1:
                        prev_errata = f"{unversioned_name}-errata{errata_num - 1}.html"
                        try:
                            with open(csv_path, "r", newline="") as csvf:
                                csv_content = csvf.read()
                            if prev_errata in csv_content:
                                echo_good("PASS: Errata set numbering is sequential")
                            else:
                                echo_error(
                                    f"FAIL: {file} is errata set {errata_num} but the previous "
                                    f"errata set {prev_errata} was not found on openid.net. "
                                    "Errata set numbers must be sequential."
                                )
                                doc_fails = True
                        except FileNotFoundError:
                            pass

            # Both ERRATA and DRAFT_ERRATA require a predecessor final spec
            if final_exists_in_csv(unversioned_name, csv_path):
                echo_good("PASS: A predecessor final spec exists")
            else:
                echo_error(f"FAIL: {file} is an errata but no predecessor Final spec was found on openid.net. An errata can only be published after the spec has reached Final.")
                doc_fails = True
        else:
            expected_draft = f"'Draft {draft_num_match.group(1)}'" if draft_num_match else "'Draft NN'"
            echo_error(
                f"FAIL: Cannot tell whether {file} is a draft, Implementer's Draft, "
                f"Final or errata. Its title is '{found_title}'. A draft's title must end "
                f"with {expected_draft} (the number in the filename), an errata's title "
                "must say 'incorporating errata set N', and a Final must have "
                "'Status: Final' in the document header."
            )
            doc_fails = True
            state_unknown = True

        print("Checking for draft disclaimer")
        # -- Draft disclaimer must not appear in FINAL or ERRATA -------------
        if state in ("FINAL", "ERRATA"):
            if spec_validator.check_draft_disclaimer(content):
                echo_error(
                    f"FAIL: {file} contains 'This document is not an OIDF International Standard' "
                    "which must be removed for Final and Errata publications"
                )
                doc_fails = True
            else:
                echo_good(f"PASS: No draft disclaimer in {file}")

        print("Checking for IETF IPR boilerplate")
        # -- IETF IPR boilerplate must not be present ---
        found_ipr = spec_validator.check_ietf_ipr(content)
        if found_ipr:
            matched = ", ".join(f"'{s}'" for s in found_ipr)
            echo_error(
                f"FAIL: {file} contains IETF Internet-Draft boilerplate ({matched}). "
                "OIDF specs must not include the IETF 'Status of This Memo' or IETF "
                "copyright notice. If the source is markdown, set ipr = \"none\" and "
                "remove the [seriesInfo] Internet-Draft block from the front matter, "
                "then regenerate the HTML."
            )
            doc_fails = True
        else:
            echo_good(f"PASS: No IETF Internet-Draft boilerplate in {file}")

        print("Checking for 'OIDC' usage")
        # -- 'OIDC' must not be used; the official name is 'OpenID Connect' --
        oidc_lines = spec_validator.check_oidc_usage(content)
        if oidc_lines:
            lines_str = _first_few([str(n) for n in oidc_lines], limit=10)
            if state in ("FINAL", "ERRATA"):
                echo_error(
                    f"FAIL: {file} contains 'OIDC' (HTML lines {lines_str}). "
                    "For branding reasons OIDF specs must use the official name 'OpenID Connect', "
                    "not the unofficial abbreviation 'OIDC'."
                )
                doc_fails = True
            else:
                echo_warn(
                    f"WARNING: {file} contains 'OIDC' (HTML lines {lines_str}). "
                    "For branding reasons please replace with the official name 'OpenID Connect' "
                    "before final publication."
                )
        else:
            echo_good(f"PASS: No 'OIDC' in {file}")

        print("Checking title consistency")
        # -- Title consistency (<title> vs <h1>) ----------------------------
        if not title_result["match"]:
            echo_error(f"FAIL: Title tag does not match H1 heading in {file}.")
            echo_info(f"  <title>: {title_result['title_tag'][:100] if title_result['title_tag'] else 'not found'}")
            echo_info(f"  <h1>: {title_result['h1_title'][:100] if title_result['h1_title'] else 'not found'}")
            doc_fails = True
        else:
            echo_good(f"PASS: Title tag matches H1 heading in {file}")

        print("Checking filename matches content")
        # -- Content-filename match ----------------------------------------
        # Skip for DRAFT_ERRATA: filename is DRAFT-style (-01.html) but content
        # has errata keywords, so content_filename_match can't reconcile them.
        # content_state() already validated the DRAFT_ERRATA combination.
        if state == "DRAFT_ERRATA":
            echo_good(f"PASS: Content matches filename in {file} (DRAFT_ERRATA)")
        elif state_unknown:
            echo_info("  Skipping filename/title comparison: the document state could not be determined (see above)")
        else:
            match_result = spec_validator.content_filename_match(content, base_html, debug)
            if not match_result["match"]:
                # Give a specific hint when a -final filename lacks Status: Final in header
                filename_state_result = spec_validator.filename_state(base_html)
                if filename_state_result["state"] == "FINAL" and state != "FINAL":
                    echo_error(
                        f"FAIL: Filename indicates Final but document header does not contain "
                        f"'Status: Final'. Add <dd class=\"intended-status\">Final</dd> or "
                        f"<td class=\"header\">Final</td> to the document header in {file}."
                    )
                else:
                    echo_error(
                        f"FAIL: Content state or version number does not match filename in {file}. "
                        f"The filename says {match_result['filename_says']} "
                        f"but the title '{found_title}' says {match_result['content_says']}. "
                        "Change the title or the filename so they agree."
                    )
                doc_fails = True
            else:
                echo_good(f"PASS: Content matches filename in {file}")

        print("Checking authors")
        # -- Authors -------------------------------------------------------
        authors_result = spec_validator.content_authors(content, debug)
        if not authors_result["authors"]:
            echo_error(f"FAIL: Problem with authors in {file}. The HTML must have an authors section with at least one name and affiliation.")
            echo_info("  Looked for <dd class=\"authors\"> (div format) and <table> (table format)")
            doc_fails = True
        else:
            echo_good(f"PASS: Authors section in {file} is good")

        print("Checking notices")
        # -- Notices -------------------------------------------------------
        notices_result = spec_validator.content_notices(content, debug)
        if not notices_result["notices"]:
            echo_error(
                f"FAIL: Problem with Notices section in {file}: no 'Notices' heading was found. "
                "The document needs an appendix headed 'Notices' containing the OIDF "
                "copyright and license text from the OIDF IPR Policy, section VII."
            )
            echo_info(
                "  Accepted heading markup: <h2 id=\"name-notices\">Notices</h2> (xml2rfc), "
                "<h3>Appendix C.&nbsp; Notices</h3>, or "
                "<a href=\"#name-notices\" class=\"section-name selfRef\">Notices</a>"
            )
            doc_fails = True
        elif not notices_result["license_text_present"]:
            shown = _first_few([f"'{phrase}'" for phrase in notices_result["missing_phrases"]], sep="; ")
            echo_error(
                f"FAIL: Problem with Notices section in {file}: the OIDF license text is "
                f"incomplete. Could not find: {shown}. The Notices must contain the exact "
                "wording from the OIDF IPR Policy, section VII."
            )
            echo_info("  Only text inside <p> paragraphs is compared, after collapsing whitespace and straightening quotes.")
            doc_fails = True
        else:
            echo_good(f"PASS: Notices section in {file} is good")

        print("Checking references")
        # -- References (with URL check) -----------------------------------
        ref_result = spec_validator.content_ref(content, check_url=True, debug=debug)
        if report_reference_results(file, ref_result):
            doc_fails = True

        print("Checking reference URLs")
        # -- OpenID references should use canonical URLs ---
        non_canonical = spec_validator.check_noncanonical_refs(content)
        if non_canonical:
            shown = _first_few([f"{url} ({_n_links(count)})" for url, count in non_canonical])
            echo_warn(
                f"WARNING: {file} references editor's draft URLs instead of "
                f"https://openid.net/specs/: {shown}. Published specs "
                "should cite the canonical openid.net URL of the referenced spec."
            )
        else:
            echo_good(f"PASS: No non-canonical OpenID reference URLs in {file}")

        print("Checking workgroup")
        # -- Workgroup must match the WG directory (issue publication#192) --
        workgroup = spec_validator.content_workgroup(content)
        wg_dir = os.path.dirname(file)
        allowed_workgroups = WG_WORKGROUP_NAMES.get(wg_dir)
        if not workgroup:
            echo_warn(
                f"WARNING: No workgroup found in {file}. The spec source should "
                f"set the workgroup metadata to the working group's name."
            )
        elif allowed_workgroups is None:
            echo_warn(
                f"WARNING: No known workgroup names for directory '{wg_dir}' - "
                f"cannot check workgroup '{workgroup}' in {file}. Please update "
                f"WG_WORKGROUP_NAMES in publication-checks process.py."
            )
        elif workgroup.lower() in {w.lower() for w in allowed_workgroups}:
            echo_good(f"PASS: Workgroup '{workgroup}' in {file} is valid for the '{wg_dir}' directory")
        else:
            echo_error(
                f"FAIL: {file} has workgroup '{workgroup}', which is not a known "
                f"workgroup name for the '{wg_dir}' directory. Expected one of: "
                f"{', '.join(sorted(allowed_workgroups))}. Fix the workgroup in the "
                "spec source and regenerate the HTML."
            )
            doc_fails = True

        print("Checking document structure")
        # -- Structure -----------------------------------------------------
        struct_result = spec_validator.content_struct(content, debug)
        required_sections = [
            "ABSTRACT", "INTRODUCTION", "REFERENCES",
            "NORMATIVE_REFERENCES", "ACKNOWLEDGEMENTS", "SECURITY",
        ]
        struct_ok = all(
            struct_result["structure"].get(s) for s in required_sections
        )
        if not struct_ok:
            missing = [s for s in required_sections if not struct_result["structure"].get(s)]
            found = [s for s in required_sections if struct_result["structure"].get(s)]
            names = {s: spec_validator.SECTION_DESCRIPTIONS[s][0] for s in required_sections}
            echo_error(
                f"FAIL: Problem with structure in {file}. Missing sections: "
                f"{', '.join(names[s] for s in missing)}. Sections are recognised by "
                "their headings; the lines below say what was looked for."
            )
            if found:
                echo_info(f"  Sections found: {', '.join(names[s] for s in found)}")
            # Say in plain words what markup is expected, and keep the regex so
            # anyone debugging a near-miss can see exactly what is matched.
            for section in missing:
                echo_info(f"  {names[section]}: looked for {spec_validator.SECTION_DESCRIPTIONS[section][1]}")
                echo_info(f"    (regex: {spec_validator.PATTERNS.get(section, '?')})")
            doc_fails = True
        else:
            echo_good(f"PASS: Structure of {file} is good")
            echo_good(
                " This indicates that Abstract, Introduction, References, "
                "Normative References, Informative References, "
                "Acknowledgements and Security Considerations sections are all present"
            )

        print("Checking publication date")
        # -- Publication date ----------------------------------------------
        today = os.environ.get("OVERRIDE_TODAY") or datetime.date.today().isoformat()
        print(f"Today is: {today}")

        date_result, _ = spec_validator.content_date(content, compare_date=today, debug=debug)

        # Print date output similar to shell
        print("Content Date:")
        for k, v in date_result.items():
            if k != "debug":
                print(f"  {k}: {v}")

        days_old = None
        if "comparison" in date_result:
            days_old = date_result["comparison"].get("days_difference")

        if days_old is not None:
            print(f"{days_old} days since publication")
            if days_old > 10:
                echo_error(f"FAIL: Publication date is more than 10 days ago in {file}.")
                echo_info(f"  Publication date found: {date_result.get('date', 'none')}")
                echo_info(f"  Compared against: {today}")
                doc_fails = True
            else:
                echo_good(f"PASS: Publication date of {file} is good")
        else:
            echo_error(f"FAIL: Could not determine publication date in {file}. Ensure the HTML contains a published date element.")
            doc_fails = True

        # -- Copyright year must match the publication year ---------------
        # Only when a Notices section exists; without one the Notices check
        # above has already asked for the whole appendix.
        if notices_result["notices"]:
            copyright_year = date_result["copyright_date"]
            if copyright_year == "Copyright date not found":
                echo_error(
                    f"FAIL: Could not find 'Copyright (c) YYYY The OpenID Foundation' in the "
                    f"Notices of {file}. The Notices must start with the OIDF copyright line."
                )
                doc_fails = True
            elif days_old is None:
                pass  # no publication date: already reported above
            elif not date_result["years_match"]:
                published_date = date_result["date"]
                echo_error(
                    f"FAIL: Copyright year in the Notices of {file} is {copyright_year} but the "
                    f"publication date is {published_date}. Update the copyright year to "
                    f"{published_date[:4]}."
                )
                doc_fails = True
            else:
                echo_good(f"PASS: Copyright year {copyright_year} in {file} matches the publication date")

        # -- Per-file summary ----------------------------------------------
        if doc_fails:
            any_fails = True
            echo_error(f"FAIL: {file} did not pass all checks")
        else:
            echo_good(f"CONGRATULATIONS: {file} passed all checks")

        print("-" * 114)
        print("-" * 114)

    # ---- Final summary ---------------------------------------------------
    print("All checks completed")

    if any_fails:
        echo_error(
            "Process exiting in a fail state - one or more of the submitted "
            "html documents failed at least one check"
        )
        echo_error(
            "Guidance on how to fix each FAIL state is provided at "
            "https://github.com/openid/publication/blob/main/ERROR-MODES.md"
        )
        return 1

    echo_good("CONGRATULATIONS: all submitted files passed all checks")
    print("-" * 114)
    return 0


if __name__ == "__main__":
    sys.exit(main())
