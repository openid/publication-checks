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
| IMPLEMENTERS | "Implementers Draft N" | No | `spec-1_0-ID1.html` |

Draft numbers start at -00 and must be zero-padded (two digits).

## Running Tests

```bash
pip install -r requirements.txt
python3 -m pytest tests/ -v                    # all tests
python3 -m pytest tests/ -m "not e2e"          # unit tests only (no network)
python3 -m pytest tests/ -m e2e                # e2e tests (needs network)
python3 -m pytest tests/ -m e2e -k "not pr161" # e2e without PR #161 tests
```

E2e tests create temporary git repos and run process.py/publish.py against them. They require network access to fetch the spec list from openid.net.

## Key Patterns

- FINAL state is detected from HTML header metadata (`<dd class="intended-status">Final</dd>` or `<td class="header">Final</td>`), NOT from the title tag.
- The PATTERNS dict in spec_validator.py defines all regex patterns for filename and content matching.
- `process.py` and `publish.py` import from `spec_validator` directly (no subprocess calls).
- The only subprocess call is `git diff` to find changed HTML files.

## OIDF Publication Rules

The checks enforce rules from:
- https://openid.net/wg/resources/naming-and-contents-of-specifications/
- https://openid.net/wg/resources/publishing-specifications/
- https://openid.net/wg/resources/approving-specifications/
