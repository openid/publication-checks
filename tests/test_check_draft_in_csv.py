import importlib
import os
import sys

import pytest

# Import the module with a hyphenated name
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
cli_tool = importlib.import_module("cli-tool")


class TestDraftNotInCsv:
    """Test that filenames NOT present in the CSV return EXIT_SUCCESS."""

    def test_new_spec_not_in_csv(self, tmp_csv):
        result = cli_tool.check_draft_in_csv("new-spec-1_0-01.html", csv_file=tmp_csv)
        assert result == cli_tool.EXIT_SUCCESS

    def test_different_draft_number_not_in_csv(self, tmp_csv):
        """A draft number that differs from what is in the CSV should not match."""
        result = cli_tool.check_draft_in_csv("openid-connect-discovery-1_0-22.html", csv_file=tmp_csv)
        assert result == cli_tool.EXIT_SUCCESS

    def test_final_not_in_csv(self, tmp_csv):
        """A final filename that is not in the CSV should return success."""
        result = cli_tool.check_draft_in_csv("openid-federation-1_0-final.html", csv_file=tmp_csv)
        assert result == cli_tool.EXIT_SUCCESS


class TestDraftFoundInCsv:
    """Test that filenames present in the CSV return EXIT_DRAFT_FOUND_IN_CSV."""

    def test_draft_found_in_csv(self, tmp_csv):
        result = cli_tool.check_draft_in_csv(
            "openid-connect-discovery-1_0-21.html", csv_file=tmp_csv
        )
        assert result == cli_tool.EXIT_DRAFT_FOUND_IN_CSV

    def test_final_found_in_csv(self, tmp_csv):
        """A final filename that IS in the CSV should be flagged."""
        result = cli_tool.check_draft_in_csv(
            "openid-connect-core-1_0-final.html", csv_file=tmp_csv
        )
        assert result == cli_tool.EXIT_DRAFT_FOUND_IN_CSV


class TestInvalidFilename:
    """Test that invalid filenames return EXIT_INVALID_DRAFT_FILENAME."""

    def test_plain_text_file(self, tmp_csv):
        result = cli_tool.check_draft_in_csv("readme.txt", csv_file=tmp_csv)
        assert result == cli_tool.EXIT_INVALID_DRAFT_FILENAME

    def test_no_extension(self, tmp_csv):
        result = cli_tool.check_draft_in_csv("openid-connect-core-1_0-01", csv_file=tmp_csv)
        assert result == cli_tool.EXIT_INVALID_DRAFT_FILENAME

    def test_empty_string(self, tmp_csv):
        result = cli_tool.check_draft_in_csv("", csv_file=tmp_csv)
        assert result == cli_tool.EXIT_INVALID_DRAFT_FILENAME

    def test_current_filename_rejected(self, tmp_csv):
        """A CURRENT-style filename (no draft/final suffix) should be invalid."""
        result = cli_tool.check_draft_in_csv("openid-connect-core-1_0.html", csv_file=tmp_csv)
        assert result == cli_tool.EXIT_INVALID_DRAFT_FILENAME


class TestMissingCsvFile:
    """Test that a missing CSV file returns EXIT_FILE_NOT_FOUND."""

    def test_missing_csv(self, tmp_path):
        nonexistent = str(tmp_path / "nonexistent.csv")
        result = cli_tool.check_draft_in_csv("new-spec-1_0-01.html", csv_file=nonexistent)
        assert result == cli_tool.EXIT_FILE_NOT_FOUND


class TestPathPrefixStripped:
    """Test that directory prefixes are stripped so only the basename is checked."""

    def test_path_prefix_stripped_found(self, tmp_csv):
        """A path like 'connect/filename.html' should match on the basename only."""
        result = cli_tool.check_draft_in_csv(
            "connect/openid-connect-discovery-1_0-21.html", csv_file=tmp_csv
        )
        assert result == cli_tool.EXIT_DRAFT_FOUND_IN_CSV

    def test_path_prefix_stripped_not_found(self, tmp_csv):
        result = cli_tool.check_draft_in_csv(
            "drafts/new-spec-1_0-01.html", csv_file=tmp_csv
        )
        assert result == cli_tool.EXIT_SUCCESS

    def test_absolute_path_prefix_stripped(self, tmp_csv):
        result = cli_tool.check_draft_in_csv(
            "/home/user/specs/openid-connect-discovery-1_0-21.html", csv_file=tmp_csv
        )
        assert result == cli_tool.EXIT_DRAFT_FOUND_IN_CSV
