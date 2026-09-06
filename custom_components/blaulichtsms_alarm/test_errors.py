"""Unit tests for the API exception hierarchy."""

import unittest

from .errors import BlaulichtSmsApiError, BlaulichtSmsAuthError, BlaulichtSmsError


class TestErrors(unittest.TestCase):
    """Tests for the exception hierarchy."""

    def test_api_error_keeps_result_and_description(self):
        """The API error exposes result code and description."""
        err = BlaulichtSmsApiError("INVALID_GROUP", "group G9 unknown")
        self.assertEqual(err.result, "INVALID_GROUP")
        self.assertEqual(err.description, "group G9 unknown")
        self.assertEqual(str(err), "INVALID_GROUP: group G9 unknown")

    def test_api_error_without_description(self):
        """A missing description leaves the message at the result code."""
        err = BlaulichtSmsApiError("UNKNOWN_ERROR")
        self.assertIsNone(err.description)
        self.assertEqual(str(err), "UNKNOWN_ERROR")

    def test_auth_error_is_an_api_error(self):
        """Auth errors can be caught as API errors and as base errors."""
        err = BlaulichtSmsAuthError("UNKNOWN_USER", "no such user")
        self.assertIsInstance(err, BlaulichtSmsApiError)
        self.assertIsInstance(err, BlaulichtSmsError)


if __name__ == "__main__":
    unittest.main()
