"""Unit tests for process.report_reference_results()."""

import os
import sys

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)
sys.path.insert(0, os.path.join(_TESTS_DIR, ".."))

from process import report_reference_results  # noqa: E402


class TestReportReferenceResults:

    def test_all_accessible_passes(self, capsys):
        ref_result = {
            "all_accessible": True,
            "inaccessible_urls": [],
            "unverified_urls": [],
        }
        failed = report_reference_results("spec.html", ref_result)
        out = capsys.readouterr().out
        assert failed is False
        assert "PASS: References in spec.html is good" in out

    def test_inaccessible_urls_fail_and_are_listed(self, capsys):
        ref_result = {
            "all_accessible": False,
            "inaccessible_urls": ["https://example.com/b", "https://example.com/a"],
            "unverified_urls": [],
        }
        failed = report_reference_results("spec.html", ref_result)
        out = capsys.readouterr().out
        assert failed is True
        assert "FAIL: Problem with References in spec.html" in out
        assert "https://example.com/a, https://example.com/b" in out
        assert "PASS" not in out

    def test_unverified_urls_warn_without_failing(self, capsys):
        ref_result = {
            "all_accessible": True,
            "inaccessible_urls": [],
            "unverified_urls": ["https://www.iso.org/standard/70907.html"],
        }
        failed = report_reference_results("spec.html", ref_result)
        out = capsys.readouterr().out
        assert failed is False
        assert "WARNING: Could not verify these referenced URLs in spec.html" in out
        assert "https://www.iso.org/standard/70907.html" in out
        assert "FAIL" not in out
        assert "PASS" not in out

    def test_inaccessible_and_unverified_together(self, capsys):
        ref_result = {
            "all_accessible": False,
            "inaccessible_urls": ["https://example.com/dead"],
            "unverified_urls": ["https://www.iso.org/standard/70907.html"],
        }
        failed = report_reference_results("spec.html", ref_result)
        out = capsys.readouterr().out
        assert failed is True
        assert "FAIL: Problem with References in spec.html" in out
        assert "WARNING: Could not verify these referenced URLs in spec.html" in out
