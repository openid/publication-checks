# OIDF publication-checks

Validation tools for the OpenID Foundation specification publication pipeline.

Performs automated checks on proposed specifications submitted via pull requests to the [openid/publication](https://github.com/openid/publication) repository.

## Structure

- `spec_validator.py` - Core validation library. Regex-based HTML analysis for spec structure, state detection, dates, notices, references, authors, history. Also works as CLI (`python3 spec_validator.py -content-state file.html`).
- `process.py` - Pre-publication validation. Runs all checks against proposed specs. Called by GitHub Actions on `propose/**` branches.
- `publish.py` - Publication file preparation. Copies spec files to `to-publish/` with correct naming for DRAFT/FINAL/ERRATA/DRAFT_ERRATA states. Called by GitHub Actions on merge to main.

## Running Tests

```bash
pip install -r requirements.txt
python3 -m pytest tests/ -v                    # all tests
python3 -m pytest tests/ -m "not e2e"          # unit tests only
python3 -m pytest tests/ -m e2e                # e2e tests
```

E2e tests create temporary git repos and run process.py/publish.py against them. Network access is not required — CSV fetching is skipped via `SKIP_CSV_FETCH` and URL accessibility checks are mocked via `MOCK_URL_CHECK` (both set automatically by the test helper).

## Checks Performed

See [CLAUDE.md](CLAUDE.md) for a detailed list of all checks and the OIDF rules they enforce.

Reference URL checks fall back to the Internet Archive Wayback Machine when a site blocks automated requests (HTTP 403/429): a snapshot means the URL passes, no snapshot means it fails, and an unreachable archive produces a non-blocking warning.

See [ERROR-MODES.md](https://github.com/openid/publication/blob/main/ERROR-MODES.md) in the publication repo for guidance on fixing each failure.
