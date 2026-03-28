#!/usr/bin/env python3
"""Python replacement for publish.sh -- publication file preparation.

Calls spec_validator functions directly instead of spawning
``python cli-tool.py`` as a subprocess.  The only subprocess call is
``git diff`` to discover changed HTML files.

For each changed HTML file the script determines the document state
(DRAFT / FINAL / ERRATA) and copies the HTML plus companion files
(.zip, .md, .xml, .txt) into ``../to-publish/`` with appropriate
versioned, unversioned, and state-suffixed names.

Exit codes:
    0 -- all files processed successfully
    1 -- one or more critical failures
"""
from __future__ import annotations

import csv
import os
import re
import shutil
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
# Colour helpers (ANSI escape codes, same palette as publish.sh)
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _copy_file(src: str, dst: str) -> bool:
    """Copy *src* to *dst* using shutil.copy2.  Return True on success."""
    try:
        shutil.copy2(src, dst)
        return True
    except (OSError, FileNotFoundError):
        return False


def _lookup_next_errata(unversioned_name: str, csv_path: str) -> int:
    """Find the highest existing errata number for *unversioned_name* and return next."""
    pattern = re.compile(re.escape(unversioned_name) + r"-errata(\d)\.html")
    existing_numbers: list[int] = []
    try:
        with open(csv_path, "r", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if row:
                    m = pattern.search(row[0])
                    if m:
                        existing_numbers.append(int(m.group(1)))
    except FileNotFoundError:
        pass

    if existing_numbers:
        return max(existing_numbers) + 1
    return 1


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def main() -> int:
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    any_fails = False
    published_links: list[str] = []

    # ---- Fetch spec-list.csv ---------------------------------------------
    csv_path = os.path.join(_SCRIPT_DIR, "spec-list.csv")
    if os.path.isfile(csv_path) and os.environ.get("SKIP_CSV_FETCH"):
        print("Using existing spec-list.csv (SKIP_CSV_FETCH is set)")
    else:
        csv_data = spec_validator.get_spec_list_csv()
        if csv_data is None:
            echo_error("OpenID Specs not available. Exiting script.")
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

    # Write changed HTML filenames to delete_files.txt
    with open("delete_files.txt", "w") as df:
        df.write(" ".join(changed_files) + "\n" if changed_files else "\n")

    # Export CHANGEDFILES env var (available to child processes / workflow)
    os.environ["CHANGEDFILES"] = " ".join(changed_files)

    print(os.getcwd())
    print(f"Number of new files detected: {CYAN}{len(changed_files)}{NC}")

    if debug:
        for cf in changed_files:
            print(cf)

    print("List of changed files detected: ")
    subdirectories: list[str] = []
    for file in changed_files:
        echo_info(file)
        subdirectories.append(os.path.dirname(file))

    unique_dirs = sorted(set(subdirectories))
    print(f"Sub-Directories: {len(unique_dirs)}")

    # ---- No HTML files? --------------------------------------------------
    if not changed_files:
        echo_error("FAIL: No HTML files have changed.  Exiting script.")
        return 1

    # ---- Process each changed HTML file ----------------------------------
    to_publish = os.path.join("..", "to-publish")

    for file in changed_files:
        html_fails = False
        md_fails = False
        xml_fails = False
        doc_fails = False

        print("-" * 114)
        print(f"Processing file: {file}")

        file_path = os.path.join("..", file)

        # -- Document state ------------------------------------------------
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                content = fh.read()
        except (FileNotFoundError, PermissionError) as exc:
            echo_error(f"ERROR: Cannot read {file}: {exc}")
            any_fails = True
            print("-" * 114)
            continue

        state_result = spec_validator.content_state(content, debug)
        state = state_result["state"]

        # Print state output similar to shell
        print(f"Running -content-state")
        for k, v in state_result.items():
            if k != "debug":
                print(f"  {k}: {v}")

        # -- Derive versioned / unversioned names --------------------------
        versioned_name = os.path.splitext(os.path.basename(file))[0]
        if debug:
            print(versioned_name)

        if versioned_name.endswith("-final"):
            unversioned_name = versioned_name[:-6]
        elif re.search(r'-ID\d$', versioned_name):
            unversioned_name = re.sub(r'-ID\d$', '', versioned_name)
        else:
            unversioned_name = re.sub(r'-\d{1,2}$', '', versioned_name)

        if debug:
            print(unversioned_name)

        dir_of_file = os.path.dirname(file)

        # -- State-specific copying ----------------------------------------
        if state == "UNKNOWN":
            echo_error("Problem with document titles so state is UNKNOWN.  EXITING")
            return 1

        elif state == "DRAFT":
            print("Do DRAFT copies")
            _do_draft_copies(
                file, file_path, dir_of_file, versioned_name,
                unversioned_name, to_publish, published_links,
            )
            html_fails, md_fails, xml_fails = _check_copy_results(
                versioned_name, unversioned_name, to_publish,
            )

        elif state == "FINAL":
            print("Do FINAL copies")
            _do_final_copies(
                file, file_path, dir_of_file, versioned_name,
                unversioned_name, to_publish, published_links,
            )
            html_fails, md_fails, xml_fails = _check_copy_results(
                versioned_name, unversioned_name, to_publish,
                state_suffix="-final",
            )

        elif state == "IMPLEMENTERS":
            print("Do IMPLEMENTERS copies")
            _do_draft_copies(
                file, file_path, dir_of_file, versioned_name,
                unversioned_name, to_publish, published_links,
            )
            html_fails, md_fails, xml_fails = _check_copy_results(
                versioned_name, unversioned_name, to_publish,
            )

        elif state == "DRAFT_ERRATA":
            print("Do DRAFT_ERRATA copies (versioned only – does not overwrite unversioned final)")
            _do_draft_errata_copies(
                file, file_path, dir_of_file, versioned_name,
                to_publish, published_links,
            )
            html_fails = not os.path.exists(
                os.path.join(to_publish, os.path.basename(file))
            )
            md_fails = not os.path.exists(
                os.path.join(to_publish, f"{versioned_name}.md")
            )
            xml_fails = not os.path.exists(
                os.path.join(to_publish, f"{versioned_name}.xml")
            )

        elif state == "ERRATA":
            print("Do ERRATA copies")
            next_errata = _lookup_next_errata(unversioned_name, csv_path)
            print(f"Next Errata increment: {next_errata}")
            errata_suffix = f"-errata{next_errata}"
            _do_errata_copies(
                file, file_path, dir_of_file, versioned_name,
                unversioned_name, errata_suffix, to_publish,
                published_links,
            )
            html_fails, md_fails, xml_fails = _check_copy_results(
                versioned_name, unversioned_name, to_publish,
                state_suffix=errata_suffix,
            )

        else:
            echo_error(f"FAIL: Unexpected document state: {state}")
            echo_error(
                "FAIL: this may be due to incorrect file name format "
                "or heading suffix issues"
            )
            doc_fails = True

        # -- Per-file result checks ----------------------------------------
        if html_fails:
            echo_error(
                f"FAIL: {file} either a file state error or HTML copy error occured"
            )
            any_fails = True
            doc_fails = True

        if md_fails and xml_fails:
            echo_error(
                f"FAIL: {file} requires corresponding source as either .md or .xml"
            )
            any_fails = True
            doc_fails = True

        if doc_fails:
            any_fails = True
            echo_error(f"FAIL: {file} did not pass all checks")
        else:
            echo_good(f"CONGRATULATIONS: {file} prepartion successful")

        print("-" * 114)

    # ---- Final summary ---------------------------------------------------
    print("All checks completed")

    if any_fails:
        echo_error(
            "Process exiting in a fail state - there was a critical failure "
            "with on or more of the documents"
        )
        return 1

    echo_good("CONGRATULATIONS: publish prep complete")
    echo_good("Links:")
    for link in published_links:
        echo_good(link)

    print("-" * 114)
    print("-" * 114)
    return 0


# ---------------------------------------------------------------------------
# Copy logic per state
# ---------------------------------------------------------------------------

def _do_draft_copies(
    file: str,
    file_path: str,
    dir_of_file: str,
    versioned_name: str,
    unversioned_name: str,
    to_publish: str,
    published_links: list[str],
) -> None:
    """DRAFT: copy versioned + unversioned for each extension."""
    basename = os.path.basename(file)

    # .html -- mandatory
    if _copy_file(file_path, os.path.join(to_publish, basename)):
        published_links.append(f"https://openid.net/specs/{basename}")
        _copy_file(file_path, os.path.join(to_publish, f"{unversioned_name}.html"))
        published_links.append(f"https://openid.net/specs/{unversioned_name}.html")
        print("successful html copies")
    else:
        echo_error(f"ERROR: Mandatory copy of {file} failed")

    # optional companion extensions
    for ext in ("zip", "md", "xml", "txt"):
        src = os.path.join("..", dir_of_file, f"{versioned_name}.{ext}")
        if _copy_file(src, os.path.join(to_publish, f"{versioned_name}.{ext}")):
            published_links.append(
                f"https://openid.net/specs/{versioned_name}.{ext}"
            )
            _copy_file(src, os.path.join(to_publish, f"{unversioned_name}.{ext}"))
            published_links.append(
                f"https://openid.net/specs/{unversioned_name}.{ext}"
            )
            print(f"successful {ext} copies")
        else:
            echo_warn(f"WARNING: copy of {versioned_name}.{ext} failed")


def _do_final_copies(
    file: str,
    file_path: str,
    dir_of_file: str,
    versioned_name: str,
    unversioned_name: str,
    to_publish: str,
    published_links: list[str],
) -> None:
    """FINAL: copy versioned + unversioned + -final for each extension."""
    basename = os.path.basename(file)

    # .html -- mandatory
    if _copy_file(file_path, os.path.join(to_publish, basename)):
        published_links.append(f"https://openid.net/specs/{basename}")
        _copy_file(file_path, os.path.join(to_publish, f"{unversioned_name}.html"))
        published_links.append(f"https://openid.net/specs/{unversioned_name}.html")
        _copy_file(file_path, os.path.join(to_publish, f"{unversioned_name}-final.html"))
        published_links.append(f"https://openid.net/specs/{unversioned_name}-final.html")
        print("successful html copies")
    else:
        echo_error(f"ERROR: Mandatory copy of {file} failed")

    # optional companion extensions
    for ext in ("zip", "md", "xml", "txt"):
        src = os.path.join("..", dir_of_file, f"{versioned_name}.{ext}")
        if _copy_file(src, os.path.join(to_publish, f"{versioned_name}.{ext}")):
            published_links.append(
                f"https://openid.net/specs/{versioned_name}.{ext}"
            )
            _copy_file(src, os.path.join(to_publish, f"{unversioned_name}.{ext}"))
            published_links.append(
                f"https://openid.net/specs/{unversioned_name}.{ext}"
            )
            _copy_file(src, os.path.join(to_publish, f"{unversioned_name}-final.{ext}"))
            published_links.append(
                f"https://openid.net/specs/{unversioned_name}-final.{ext}"
            )
            print(f"successful {ext} copies")
        else:
            echo_warn(f"WARNING: copy of {versioned_name}.{ext} failed")


def _do_draft_errata_copies(
    file: str,
    file_path: str,
    dir_of_file: str,
    versioned_name: str,
    to_publish: str,
    published_links: list[str],
) -> None:
    """DRAFT_ERRATA: copy versioned only — do not overwrite the unversioned final."""
    basename = os.path.basename(file)

    # .html -- mandatory
    if _copy_file(file_path, os.path.join(to_publish, basename)):
        published_links.append(f"https://openid.net/specs/{basename}")
        print("successful html copies")
    else:
        echo_error(f"ERROR: Mandatory copy of {file} failed")

    # optional companion extensions (versioned only)
    for ext in ("zip", "md", "xml", "txt"):
        src = os.path.join("..", dir_of_file, f"{versioned_name}.{ext}")
        if _copy_file(src, os.path.join(to_publish, f"{versioned_name}.{ext}")):
            published_links.append(
                f"https://openid.net/specs/{versioned_name}.{ext}"
            )
            print(f"successful {ext} copies")
        else:
            echo_warn(f"WARNING: copy of {versioned_name}.{ext} failed")


def _do_errata_copies(
    file: str,
    file_path: str,
    dir_of_file: str,
    versioned_name: str,
    unversioned_name: str,
    errata_suffix: str,
    to_publish: str,
    published_links: list[str],
) -> None:
    """ERRATA: copy versioned + unversioned + -errata# for each extension.

    This fixes the bug in publish.sh which incorrectly used ``-final``
    suffix for non-HTML errata companion files.  We correctly use the
    ``-errata#`` suffix for all extensions.
    """
    basename = os.path.basename(file)

    # .html -- mandatory
    if _copy_file(file_path, os.path.join(to_publish, basename)):
        published_links.append(f"https://openid.net/specs/{basename}")
        _copy_file(file_path, os.path.join(to_publish, f"{unversioned_name}.html"))
        published_links.append(f"https://openid.net/specs/{unversioned_name}.html")
        _copy_file(file_path, os.path.join(to_publish, f"{unversioned_name}{errata_suffix}.html"))
        published_links.append(f"https://openid.net/specs/{unversioned_name}{errata_suffix}.html")
        print("successful html copies")
    else:
        echo_error(f"ERROR: Mandatory copy of {file} failed")

    # optional companion extensions
    for ext in ("zip", "md", "xml", "txt"):
        src = os.path.join("..", dir_of_file, f"{versioned_name}.{ext}")
        if _copy_file(src, os.path.join(to_publish, f"{versioned_name}.{ext}")):
            published_links.append(
                f"https://openid.net/specs/{versioned_name}.{ext}"
            )
            _copy_file(src, os.path.join(to_publish, f"{unversioned_name}.{ext}"))
            published_links.append(
                f"https://openid.net/specs/{unversioned_name}.{ext}"
            )
            _copy_file(src, os.path.join(to_publish, f"{unversioned_name}{errata_suffix}.{ext}"))
            published_links.append(
                f"https://openid.net/specs/{unversioned_name}{errata_suffix}.{ext}"
            )
            print(f"successful {ext} copies")
        else:
            echo_warn(f"WARNING: copy of {versioned_name}.{ext} failed")


# ---------------------------------------------------------------------------
# Post-copy verification helper
# ---------------------------------------------------------------------------

def _check_copy_results(
    versioned_name: str,
    unversioned_name: str,
    to_publish: str,
    *,
    state_suffix: str | None = None,
) -> tuple[bool, bool, bool]:
    """Check which files were actually created and return failure flags.

    Returns (html_fails, md_fails, xml_fails).
    """
    html_fails = not os.path.isfile(
        os.path.join(to_publish, f"{unversioned_name}.html")
    )
    md_fails = not os.path.isfile(
        os.path.join(to_publish, f"{unversioned_name}.md")
    )
    xml_fails = not os.path.isfile(
        os.path.join(to_publish, f"{unversioned_name}.xml")
    )
    return html_fails, md_fails, xml_fails


if __name__ == "__main__":
    sys.exit(main())
