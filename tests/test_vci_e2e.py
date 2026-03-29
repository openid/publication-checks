"""
Tests against the real published VCI (Verifiable Credential Issuance) 1.0 specs.

Uses copies of the actual published HTML files as test fixtures.
"""
from __future__ import annotations

import os
import sys

import pytest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)
sys.path.insert(0, os.path.join(_TESTS_DIR, ".."))

import spec_validator  # noqa: E402

FIXTURES_DIR = os.path.join(_TESTS_DIR, "fixtures")


@pytest.fixture(scope="module")
def vci_final():
    path = os.path.join(FIXTURES_DIR, "openid-4-verifiable-credential-issuance-1_0-final.html")
    with open(path, encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def vci_draft17():
    path = os.path.join(FIXTURES_DIR, "openid-4-verifiable-credential-issuance-1_0-17.html")
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestVCIFinal:
    """Tests for the real VCI 1.0 final spec."""

    def test_filename_state(self):
        result = spec_validator.filename_state(
            "openid-4-verifiable-credential-issuance-1_0-final.html"
        )
        assert result["state"] == "FINAL"

    def test_content_state(self, vci_final):
        result = spec_validator.content_state(vci_final)
        assert result["state"] == "FINAL"

    def test_title_matches_h1(self, vci_final):
        result = spec_validator.content_title(vci_final)
        assert result["match"] is True

    def test_has_authors(self, vci_final):
        result = spec_validator.content_authors(vci_final)
        assert len(result["authors"]) >= 1

    def test_has_notices(self, vci_final):
        result = spec_validator.content_notices(vci_final)
        assert result["notices"] is True

    def test_has_license_text(self, vci_final):
        result = spec_validator.content_notices(vci_final)
        assert result["license_text_present"] is True

    def test_has_abstract(self, vci_final):
        result = spec_validator.content_struct(vci_final)
        assert result["structure"]["ABSTRACT"] is True

    def test_has_introduction(self, vci_final):
        result = spec_validator.content_struct(vci_final)
        assert result["structure"]["INTRODUCTION"] is True

    def test_has_normative_references(self, vci_final):
        result = spec_validator.content_struct(vci_final)
        assert result["structure"]["NORMATIVE_REFERENCES"] is True

    def test_has_security_considerations(self, vci_final):
        result = spec_validator.content_struct(vci_final)
        assert result["structure"]["SECURITY"] is True

    def test_has_acknowledgements(self, vci_final):
        result = spec_validator.content_struct(vci_final)
        assert result["structure"]["ACKNOWLEDGEMENTS"] is True

    def test_no_history(self, vci_final):
        result = spec_validator.content_history(vci_final)
        assert result["history_present"] is False

    def test_filename_matches_content(self, vci_final):
        result = spec_validator.content_filename_match(
            vci_final, "openid-4-verifiable-credential-issuance-1_0-final.html"
        )
        assert result["match"] is True


class TestVCIDraft17:
    """Tests for the real VCI 1.0 draft 17 spec."""

    def test_filename_state(self):
        result = spec_validator.filename_state(
            "openid-4-verifiable-credential-issuance-1_0-17.html"
        )
        assert result["state"] == "DRAFT"

    def test_content_state(self, vci_draft17):
        result = spec_validator.content_state(vci_draft17)
        assert result["state"] == "DRAFT"

    def test_has_history(self, vci_draft17):
        result = spec_validator.content_history(vci_draft17)
        assert result["history_present"] is True

    def test_title_matches_h1(self, vci_draft17):
        result = spec_validator.content_title(vci_draft17)
        assert result["match"] is True

    def test_filename_matches_content(self, vci_draft17):
        result = spec_validator.content_filename_match(
            vci_draft17, "openid-4-verifiable-credential-issuance-1_0-17.html"
        )
        assert result["match"] is True
