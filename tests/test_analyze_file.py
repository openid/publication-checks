import importlib
import os
import sys

import pytest
import responses

# Import the module with a hyphenated name
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
cli_tool = importlib.import_module("cli-tool")


class TestContentState:
    """Test analyze_file with -content-state option."""

    def test_draft_file_returns_draft_state(self, draft_html_file):
        results, exit_code = cli_tool.analyze_file(
            ["-content-state"], filename=draft_html_file
        )
        assert exit_code == cli_tool.EXIT_SUCCESS
        assert results["Content State"]["state"] == "DRAFT"

    def test_final_file_returns_final_state(self, final_html_file):
        results, exit_code = cli_tool.analyze_file(
            ["-content-state"], filename=final_html_file
        )
        assert exit_code == cli_tool.EXIT_SUCCESS
        assert results["Content State"]["state"] == "FINAL"

    def test_unknown_state_returns_error(self, tmp_path):
        """Content with no recognisable title/h1 yields EXIT_CONTENT_STATE_ERROR."""
        unknown_file = tmp_path / "openid-connect-example-1_0-01.html"
        # Omit <h1 id="title"> so that content_state cannot find both title
        # and h1, leaving the state as UNKNOWN.
        unknown_file.write_text(
            "<html><head><title>Something</title></head>"
            "<body><p>No h1 title here</p></body></html>"
        )
        results, exit_code = cli_tool.analyze_file(
            ["-content-state"], filename=str(unknown_file)
        )
        assert exit_code == cli_tool.EXIT_CONTENT_STATE_ERROR
        assert results["Content State"]["state"] == "UNKNOWN"


class TestContentStruct:
    """Test analyze_file with -content-struct option."""

    def test_valid_draft_struct(self, draft_html_file):
        results, exit_code = cli_tool.analyze_file(
            ["-content-struct"], filename=draft_html_file
        )
        assert exit_code == cli_tool.EXIT_SUCCESS
        structure = results["Document Structure"]["structure"]
        for section in ["ABSTRACT", "INTRODUCTION", "REFERENCES",
                        "NORMATIVE_REFERENCES", "ACKNOWLEDGEMENTS", "SECURITY"]:
            assert structure[section] is True, f"Expected {section} to be present"

    def test_malformed_html_missing_sections(self, tmp_path, malformed_html):
        """A file missing required sections returns EXIT_CONTENT_STRUCT_ERROR."""
        malformed_file = tmp_path / "openid-connect-example-1_0-01.html"
        malformed_file.write_text(malformed_html)
        results, exit_code = cli_tool.analyze_file(
            ["-content-struct"], filename=str(malformed_file)
        )
        assert exit_code == cli_tool.EXIT_CONTENT_STRUCT_ERROR
        assert len(results["Document Structure"]["missing_required"]) > 0


class TestContentAuthors:
    """Test analyze_file with -content-authors option."""

    def test_valid_authors(self, draft_html_file):
        results, exit_code = cli_tool.analyze_file(
            ["-content-authors"], filename=draft_html_file
        )
        assert exit_code == cli_tool.EXIT_SUCCESS
        authors = results["Authors"]["authors"]
        assert len(authors) >= 1
        names = [a["name"] for a in authors]
        assert "Jane Doe" in names

    def test_no_authors_returns_error(self, tmp_path, malformed_html):
        """A file with no authors returns EXIT_CONTENT_AUTHORS_ERROR."""
        no_authors_file = tmp_path / "openid-connect-example-1_0-01.html"
        no_authors_file.write_text(malformed_html)
        results, exit_code = cli_tool.analyze_file(
            ["-content-authors"], filename=str(no_authors_file)
        )
        assert exit_code == cli_tool.EXIT_CONTENT_AUTHORS_ERROR
        assert results["Authors"]["authors"] == []


class TestGetSpecListCsv:
    """Test analyze_file with -get-spec-list-csv using mocked HTTP."""

    @responses.activate
    def test_get_spec_list_csv_writes_file(self, tmp_path):
        """Mock the HTTP request and verify the CSV file is written."""
        mock_html = (
            "<html><body><table>"
            "<tr><td>icon</td><td>openid-spec-1_0.html</td>"
            "<td>50K</td><td>2025-01-01</td></tr>"
            "<tr><td>icon</td><td>openid-other-1_0-01.html</td>"
            "<td>30K</td><td>2025-06-15</td></tr>"
            "</table></body></html>"
        )
        responses.add(
            responses.GET,
            "https://openid.net/specs/",
            body=mock_html,
            status=200,
            content_type="text/html",
        )

        output_file = str(tmp_path / "output.csv")
        results, exit_code = cli_tool.analyze_file(
            ["-get-spec-list-csv", "-output", output_file]
        )
        assert exit_code == cli_tool.EXIT_SUCCESS
        assert os.path.exists(output_file)
        content = open(output_file).read()
        assert "Filename" in content
        assert "openid-spec-1_0.html" in content

    @responses.activate
    def test_get_spec_list_csv_network_failure(self, tmp_path):
        """A network error should result in EXIT_GET_SPEC_LIST_ERROR."""
        responses.add(
            responses.GET,
            "https://openid.net/specs/",
            body=Exception("Connection refused"),
        )
        output_file = str(tmp_path / "output.csv")
        results, exit_code = cli_tool.analyze_file(
            ["-get-spec-list-csv", "-output", output_file]
        )
        assert exit_code == cli_tool.EXIT_GET_SPEC_LIST_ERROR


class TestFileNotFound:
    """Test that a nonexistent file returns EXIT_FILE_NOT_FOUND."""

    def test_missing_file(self, tmp_path):
        nonexistent = str(tmp_path / "no-such-file-1_0-01.html")
        results, exit_code = cli_tool.analyze_file(
            ["-content-state"], filename=nonexistent
        )
        assert exit_code == cli_tool.EXIT_FILE_NOT_FOUND


class TestMultipleOptions:
    """Test that multiple options can be combined in a single call."""

    def test_content_state_and_struct(self, draft_html_file):
        results, exit_code = cli_tool.analyze_file(
            ["-content-state", "-content-struct"], filename=draft_html_file
        )
        assert exit_code == cli_tool.EXIT_SUCCESS
        assert "Content State" in results
        assert "Document Structure" in results
        assert results["Content State"]["state"] == "DRAFT"

    def test_content_state_and_authors(self, draft_html_file):
        results, exit_code = cli_tool.analyze_file(
            ["-content-state", "-content-authors"], filename=draft_html_file
        )
        assert exit_code == cli_tool.EXIT_SUCCESS
        assert "Content State" in results
        assert "Authors" in results
        assert len(results["Authors"]["authors"]) >= 1

    def test_early_exit_on_first_error(self, tmp_path, malformed_html):
        """When the first option fails, later options are not processed."""
        bad_file = tmp_path / "openid-connect-example-1_0-01.html"
        bad_file.write_text(malformed_html)
        results, exit_code = cli_tool.analyze_file(
            ["-content-struct", "-content-authors"], filename=str(bad_file)
        )
        # -content-struct should fail first (missing required sections)
        assert exit_code == cli_tool.EXIT_CONTENT_STRUCT_ERROR
        # Authors should not have been processed because struct failed first
        assert "Authors" not in results


class TestNoFilenameProvided:
    """Test behaviour when no filename is given for content-analysis options."""

    def test_no_filename_returns_success(self):
        """With no filename and no network options, returns EXIT_SUCCESS."""
        results, exit_code = cli_tool.analyze_file(["-content-state"])
        assert exit_code == cli_tool.EXIT_SUCCESS
        assert results == {}
