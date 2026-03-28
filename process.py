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


def echo_error(msg: str) -> None:
    print(f"{RED}{msg}{NC}")


def echo_warn(msg: str) -> None:
    print(f"{YELLOW}{msg}{NC}")


def echo_good(msg: str) -> None:
    print(f"{GREEN}{msg}{NC}")


def echo_info(msg: str) -> None:
    print(f"{CYAN}{msg}{NC}")


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


def _check_history_references_draft(draft_num_match, history_result):
    """Return True (pass) if the history section references the current draft number."""
    if draft_num_match and history_result.get("history"):
        draft_num = draft_num_match.group(1)
        draft_int = int(draft_num)
        history_text = " ".join(str(e) for e in history_result["history"])
        # Match both padded (-01) and unpadded (-1) forms
        if f"-{draft_int:02d}" in history_text or f"-{draft_int}" in history_text:
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
    csv_data = spec_validator.get_spec_list_csv()
    if csv_data is None:
        echo_error("OpenID Specs not available. Exiting script.")
        return 1

    csv_path = os.path.join(_SCRIPT_DIR, "spec-list.csv")
    with open(csv_path, "w", newline="") as f:
        f.write(csv_data)

    # ---- Get changed HTML files via git diff ---------------------------
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
    wg_fails = False
    unique_dirs = sorted(set(subdirectories))
    if len(unique_dirs) != 1:
        echo_error("FAIL: More than one WG sub-directory updated.")
        wg_fails = True

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

        # -- Source-file checks -------------------------------------------
        zip_path = os.path.join("..", f"{stem}.zip")
        md_path = os.path.join("..", f"{stem}.md")
        xml_path = os.path.join("..", f"{stem}.xml")

        if not os.path.isfile(zip_path):
            # If md source exists and references external files, zip is required
            if os.path.isfile(md_path):
                try:
                    with open(md_path, "r", encoding="utf-8") as mdf:
                        md_content = mdf.read()
                    # Common include patterns in markdown specs
                    has_includes = bool(
                        re.search(r'\{\{[^}]+\}\}', md_content)  # {{file.md}}
                        or re.search(r'!include\b', md_content, re.IGNORECASE)
                        or re.search(r'\{%\s*include', md_content)  # {% include %}
                        or re.search(r'^#include\b', md_content, re.MULTILINE)
                    )
                    if has_includes:
                        echo_error(
                            f"FAIL: {stem}.md references external files but no .zip archive "
                            f"is provided. A .zip containing all source files is required."
                        )
                        doc_fails = True
                    else:
                        echo_warn(f"WARNING: zipped content called {stem}.zip not present.")
                except (FileNotFoundError, UnicodeDecodeError):
                    echo_warn(f"WARNING: zipped content called {stem}.zip not present.")
            else:
                echo_warn(f"WARNING: zipped content called {stem}.zip not present.")

        if not os.path.isfile(md_path) and not os.path.isfile(xml_path):
            echo_error(
                f"FAIL: Either Markdown or XML Source is required. "
                f"Either a file called {stem}.md or called {stem}.xml is required."
            )
            doc_fails = True

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
                            echo_warn(
                                f"WARNING: Previous version {prev_stem} included "
                                f"{', '.join(f'.{e}' for e in sorted(missing))} "
                                f"but this submission does not"
                            )
                        else:
                            echo_good("PASS: Companion files match previous version")
                except FileNotFoundError:
                    pass

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
            echo_error(f"FAIL: Cannot read {file}: {exc}")
            doc_fails = True
            any_fails = True
            print("-" * 114)
            print("-" * 114)
            continue

        # -- History section -----------------------------------------------
        history_result = spec_validator.content_history(content, debug)
        has_history = history_result["history_present"]

        # -- Document state ------------------------------------------------
        state_result = spec_validator.content_state(content, debug)
        state = state_result["state"]

        # Print state info similar to shell (the shell calls run_cli_tool which
        # prints the cli-tool output for -content-state and -content-history).
        print(f"Content State:")
        for k, v in state_result.items():
            if k != "debug":
                print(f"  {k}: {v}")

        print(f"Document History:")
        for k, v in history_result.items():
            if k != "debug":
                print(f"  {k}: {v}")

        # Derive versioned / unversioned names (same logic as shell)
        versioned_name = os.path.splitext(os.path.basename(file))[0]
        unversioned_name = re.sub(r'-\d{1,2}$', '', versioned_name)

        # -- State / history consistency -----------------------------------
        if state == "UNKNOWN":
            echo_error("FAIL: Problem with document titles so state is UNKNOWN")
            doc_fails = True
        elif state == "DRAFT":
            echo_good("Document is in DRAFT state")
            if has_history:
                echo_good("PASS: Document has a history section")
                if not _check_history_references_draft(draft_num_match, history_result):
                    doc_fails = True
            else:
                echo_error("FAIL: DRAFT state but does not have required history section")
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
                    "FAIL: A final spec already exists. Post-final drafts "
                    "must include 'incorporating errata set N' in the title"
                )
                doc_fails = True
        elif state == "FINAL":
            echo_good("Document is in FINAL state")
            if not has_history:
                echo_good("PASS: Document does not have a history section")
            else:
                echo_error("FAIL: FINAL state but history section exists")
                doc_fails = True
        elif state == "IMPLEMENTORS":
            echo_good("Document is in IMPLEMENTORS state")
            if not has_history:
                echo_good("PASS: Document does not have a history section")
            else:
                echo_error("FAIL: IMPLEMENTORS state but history section exists")
                doc_fails = True
        elif state in ("ERRATA", "DRAFT_ERRATA"):
            echo_good(f"Document is in {state} state")

            if state == "DRAFT_ERRATA":
                # Draft errata (pre-vote) requires history, like DRAFT
                if has_history:
                    echo_good("PASS: Document has a history section")
                    if not _check_history_references_draft(draft_num_match, history_result):
                        doc_fails = True
                else:
                    echo_error("FAIL: DRAFT_ERRATA state but does not have required history section")
                    doc_fails = True
            else:
                # Approved errata (post-vote) must not have history
                if not has_history:
                    echo_good("PASS: Document does not have a history section")
                else:
                    echo_error("FAIL: ERRATA state but history section exists")
                    doc_fails = True

            # Both ERRATA and DRAFT_ERRATA require a predecessor final spec
            if final_exists_in_csv(unversioned_name, csv_path):
                echo_good("PASS: A predecessor final spec exists")
            else:
                echo_error("FAIL: A predecessor final spec does not exist")
                doc_fails = True
        else:
            echo_error(f"FAIL: Unexpected document state: {state}")
            echo_error(
                "FAIL: this may be due to incorrect file name format or heading suffix issues"
            )
            doc_fails = True

        # -- Draft disclaimer must not appear in FINAL or ERRATA -------------
        if state in ("FINAL", "ERRATA"):
            if "This document is not an OIDF International Standard" in content:
                echo_error(
                    f"FAIL: {file} contains 'This document is not an OIDF International Standard' "
                    "which must be removed for Final and Errata publications"
                )
                doc_fails = True
            else:
                echo_good(f"PASS: No draft disclaimer in {file}")

        # -- Title consistency (<title> vs <h1>) ----------------------------
        title_result = spec_validator.content_title(content, debug)
        if not title_result["match"]:
            echo_error(f"FAIL: Title tag does not match H1 heading in {file}.")
            doc_fails = True
        else:
            echo_good(f"PASS: Title tag matches H1 heading in {file}")

        # -- Content-filename match ----------------------------------------
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
                echo_error(f"FAIL: Content state or version number does not match filename in {file}.")
            doc_fails = True
        else:
            echo_good(f"PASS: Content matches filename in {file}")

        # -- Authors -------------------------------------------------------
        authors_result = spec_validator.content_authors(content, debug)
        if not authors_result["authors"]:
            echo_error(f"FAIL: Problem with authors in {file}.")
            doc_fails = True
        else:
            echo_good(f"PASS: Authors section in {file} is good")

        # -- Notices -------------------------------------------------------
        notices_result = spec_validator.content_notices(content, debug)
        notices_ok = (
            notices_result["notices"]
            and notices_result["license_text_present"]
        )
        if not notices_ok:
            echo_error(f"FAIL: Problem with Notices section in {file}.")
            doc_fails = True
        else:
            echo_good(f"PASS: Notices section in {file} is good")

        # -- References (with URL check) -----------------------------------
        ref_result = spec_validator.content_ref(content, check_url=True, debug=debug)
        if ref_result.get("all_accessible") is False:
            echo_error(f"FAIL: Problem with References in {file}.")
            echo_error(
                "This might be due to a link not responding to HEAD request "
                "- ** known roadmap defect in this tool"
            )
            doc_fails = True
        else:
            echo_good(f"PASS: References in {file} is good")

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
            echo_error(f"FAIL: Problem with structure in {file}.")
            doc_fails = True
        else:
            echo_good(f"PASS: Structure of {file} is good")
            echo_good(
                " This indicates that Abstract, Introduction, References, "
                "Normative References, Informative References, "
                "Acknowledgements and Security Considerations sections are all present"
            )

        # -- Publication date ----------------------------------------------
        today = datetime.date.today().isoformat()
        print(f"Today is: {today}")

        date_result, _ = spec_validator.content_date(content, compare_date=today, debug=debug)

        # Print date output similar to shell
        print("Content Date:")
        for k, v in date_result.items():
            if k != "debug":
                print(f"  {k}: {v}")

        days_old = 9999
        if "comparison" in date_result:
            days_old = date_result["comparison"].get("days_difference", 9999)

        print(f"{days_old} days since publication")

        if days_old > 10:
            echo_error(f"FAIL: Publication date is more than 10 days ago in {file}.")
            doc_fails = True
        else:
            echo_good(f"PASS: Publication date of {file} is good")

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

    if any_fails or wg_fails:
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
