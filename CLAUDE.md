# OpenID Publication Checks

Validation tools for the OpenID Foundation specification publication pipeline.

## Structure

- `spec_validator.py` - Core validation library. Regex-based HTML analysis for spec structure, state detection, dates, notices, references, authors, history. Also works as CLI (`python3 spec_validator.py -content-state file.html`).
- `process.py` - Pre-publication validation. Runs all checks against proposed specs. Called by GitHub Actions on `propose/**` branches.
- `publish.py` - Publication file preparation. Copies spec files to `to-publish/` with correct naming for DRAFT/FINAL/ERRATA/DRAFT_ERRATA states. Called by GitHub Actions on merge to main.

## Document States

| State | Title pattern | History required | Example filename |
|-------|--------------|------------------|-----------------|
| DRAFT | "Spec 1.0 - Draft 01" | Yes | `spec-1_0-01.html` |
| FINAL | Status header: Final | No | `spec-1_0-final.html` |
| ERRATA | "incorporating errata set N" | No | `spec-1_0-errata1.html` |
| DRAFT_ERRATA | errata + draft in title | Yes | `spec-1_0-01.html` |
| IMPLEMENTERS | "Spec 1.0 - Draft NN" (same as DRAFT) | Yes | `spec-1_0-ID1.html` |

Draft numbers start at -00 and must be zero-padded (two digits).

## Running Tests

```bash
pip install -r requirements.txt
python3 -m pytest tests/ -v                    # all tests
python3 -m pytest tests/ -m "not e2e"          # unit tests only (no network)
python3 -m pytest tests/ -m e2e                # e2e tests
```

E2e tests create temporary git repos and run process.py/publish.py against them. No network access is required — `SKIP_CSV_FETCH` uses pre-seeded CSV data and `MOCK_URL_CHECK` makes URL accessibility checks return True without HTTP calls. The `OVERRIDE_TODAY` env var can fake the current date for tests using real fixture specs with old publication dates.

## Code Organisation Principle

**spec_validator.py** contains pure content validation: functions that take HTML/markdown content and return a result. No file I/O, no git operations, no print output.

**process.py** contains pipeline orchestration: file discovery (git diff), file I/O, CSV operations, output formatting (PASS/FAIL messages), and calls to spec_validator functions.

When adding a new check: if it examines content → add to spec_validator. If it needs the repo, filesystem, or CSV → add to process.py.

## Key Patterns

- FINAL state is detected from HTML header metadata (`<dd class="intended-status">Final</dd>`, `<dd class="status">Final</dd>`, or `<td class="header">Final</td>`), NOT from the title tag.
- The PATTERNS dict in spec_validator.py defines all regex patterns for filename and content matching.
- `process.py` and `publish.py` import from `spec_validator` directly (no subprocess calls).
- The only subprocess call is `git diff` to find changed HTML files.
- Known WG directories are discovered from `origin/main` in the publication repo, not hardcoded.

## Checks Performed by process.py

- Filename not already published (duplicate check)
- Source files exist (.md or .xml required, .zip if md has includes)
- Companion files match previous version
- Document state detected and consistent with filename
- History section present for DRAFT/DRAFT_ERRATA/IMPLEMENTERS, absent for FINAL/ERRATA
- History references current draft number
- Sequential draft numbering (warning)
- Post-final drafts must use errata title
- Title tag matches H1 heading
- Content state matches filename state
- Authors section present with affiliations
- OIDF notices and license text present
- Copyright year matches published year
- All references accessible (HEAD with GET fallback; on 403/429 or a 202 WAF challenge a URL passes if the Internet Archive has a snapshot, fails if it has none, and warns without failing if the archive is unreachable)
- Required sections present (Abstract, Introduction, References, etc.)
- Publication date within 10 days
- No IETF Trust IPR boilerplate (fail for Final/Errata, warn for drafts)
- No draft disclaimer in Final/Errata specs
- References use canonical openid.net/specs/ URLs (warning)
- WG directory is a recognised one (checked against origin/main)

On failure, process.py prints diagnostic details (in cyan) showing what was found vs expected - title/h1 values, detected states, document headings, etc. These appear in the full log but not in the PR comment summary.

## OIDF Publication Rules

The checks enforce rules from:
- https://openid.net/wg/resources/naming-and-contents-of-specifications/
- https://openid.net/wg/resources/publishing-specifications/
- https://openid.net/wg/resources/approving-specifications/
- OIDF Process Document V1.98 (2024-10-19)
- OIDF IPR Policy V1.28 (2024-10-19) - Section VII defines required notice text
