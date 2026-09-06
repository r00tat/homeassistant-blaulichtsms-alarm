"""Unit tests for the alarm group filter."""

import unittest

from .group_filter import (
    GroupNotAllowedError,
    GroupsRequiredError,
    parse_group_filter,
    resolve_group_codes,
)


class TestParseGroupFilter(unittest.TestCase):
    """Tests for parse_group_filter."""

    def test_none_is_an_empty_filter(self):
        """No configured filter parses to an empty list."""
        self.assertEqual(parse_group_filter(None), [])

    def test_empty_string_is_an_empty_filter(self):
        """An empty string parses to an empty list."""
        self.assertEqual(parse_group_filter("   "), [])

    def test_comma_separated_codes_are_split_and_trimmed(self):
        """Codes are split on commas and surrounding spaces are removed."""
        self.assertEqual(parse_group_filter(" G1 , G2,G3 "), ["G1", "G2", "G3"])

    def test_empty_entries_are_dropped(self):
        """Stray commas do not create empty codes."""
        self.assertEqual(parse_group_filter("G1,,G2,"), ["G1", "G2"])


class TestResolveGroupCodes(unittest.TestCase):
    """Tests for resolve_group_codes."""

    def test_without_filter_requested_codes_pass_through(self):
        """With no filter the requested codes are returned unchanged."""
        self.assertEqual(resolve_group_codes(["G1", "G9"], []), ["G1", "G9"])

    def test_without_filter_empty_request_returns_none(self):
        """With no filter and no request the API default applies."""
        self.assertIsNone(resolve_group_codes(None, []))
        self.assertIsNone(resolve_group_codes([], []))

    def test_allowed_codes_are_returned(self):
        """A subset of the filter is accepted."""
        self.assertEqual(resolve_group_codes(["G1"], ["G1", "G2"]), ["G1"])

    def test_disallowed_code_raises(self):
        """A code outside the filter aborts the call."""
        with self.assertRaises(GroupNotAllowedError) as ctx:
            resolve_group_codes(["G1", "G3"], ["G1", "G2"])
        self.assertEqual(ctx.exception.invalid, ["G3"])

    def test_all_disallowed_codes_are_reported(self):
        """Every offending code is listed in the error."""
        with self.assertRaises(GroupNotAllowedError) as ctx:
            resolve_group_codes(["G3", "G4"], ["G1"])
        self.assertEqual(ctx.exception.invalid, ["G3", "G4"])

    def test_empty_request_with_filter_raises(self):
        """With a filter set the caller must name the groups explicitly."""
        with self.assertRaises(GroupsRequiredError):
            resolve_group_codes(None, ["G1"])
        with self.assertRaises(GroupsRequiredError):
            resolve_group_codes([], ["G1"])

    def test_requested_codes_are_trimmed(self):
        """Surrounding whitespace in a request is ignored."""
        self.assertEqual(resolve_group_codes([" G1 "], ["G1"]), ["G1"])

    def test_comparison_is_case_sensitive(self):
        """Group codes are compared case sensitively."""
        with self.assertRaises(GroupNotAllowedError):
            resolve_group_codes(["g1"], ["G1"])


if __name__ == "__main__":
    unittest.main()
