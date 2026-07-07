"""Tests for publication#192: extracting the workgroup from spec HTML."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import spec_validator


class TestContentWorkgroup:
    """Test extraction of the <dd class="workgroup"> value."""

    def test_extracts_workgroup_value(self):
        html = (
            '<dl><dt class="label-workgroup">Workgroup:</dt>'
            '<dd class="workgroup">OpenID Connect</dd></dl>'
        )
        assert spec_validator.content_workgroup(html) == "OpenID Connect"

    def test_returns_none_when_absent(self):
        html = "<html><body><h1>Some Spec</h1></body></html>"
        assert spec_validator.content_workgroup(html) is None

    def test_strips_surrounding_whitespace(self):
        html = '<dd class="workgroup">\n  fapi\n</dd>'
        assert spec_validator.content_workgroup(html) == "fapi"

    def test_empty_element_returns_empty_string(self):
        html = '<dd class="workgroup"></dd>'
        assert spec_validator.content_workgroup(html) == ""

    def test_extracts_from_fixture(self, draft_html):
        # The default fixture has no workgroup element
        assert spec_validator.content_workgroup(draft_html) is None
