"""Unit tests for the config flow schemas and helpers."""

import unittest

from .const import (
    CONF_CUSTOMER_ID,
    CONF_GROUP_FILTER,
    CONF_PASSWORD,
    CONF_USE_STAGING,
    CONF_USERNAME,
)
from .schema import build_title, build_unique_id, groups_schema, user_schema


class TestUniqueId(unittest.TestCase):
    """Tests for build_unique_id."""

    def test_live_prefix(self):
        """A live entry is prefixed with live."""
        self.assertEqual(build_unique_id("100027", False), "live-100027")

    def test_staging_prefix(self):
        """A staging entry is prefixed with staging."""
        self.assertEqual(build_unique_id("100027", True), "staging-100027")


class TestTitle(unittest.TestCase):
    """Tests for build_title."""

    def test_live_title(self):
        """A live entry is titled with the customer id."""
        self.assertEqual(build_title("100027", False), "blaulichtSMS Alarm 100027")

    def test_staging_title_is_marked(self):
        """A staging entry is marked as a test account."""
        self.assertEqual(
            build_title("100027", True), "blaulichtSMS Alarm 100027 (Test)"
        )


class TestUserSchema(unittest.TestCase):
    """Tests for the credentials step schema."""

    def test_defaults_use_staging_to_false(self):
        """use_staging defaults to the live API."""
        result = user_schema()(
            {
                CONF_CUSTOMER_ID: "100027",
                CONF_USERNAME: "user",
                CONF_PASSWORD: "secret",
            }
        )
        self.assertFalse(result[CONF_USE_STAGING])

    def test_password_is_required(self):
        """A missing password is rejected."""
        with self.assertRaises(Exception):
            user_schema()({CONF_CUSTOMER_ID: "100027", CONF_USERNAME: "user"})

    def test_prefilled_defaults_are_used(self):
        """Existing values prefill the form."""
        schema = user_schema({CONF_CUSTOMER_ID: "100027", CONF_USERNAME: "user"})
        result = schema({CONF_PASSWORD: "secret"})
        self.assertEqual(result[CONF_CUSTOMER_ID], "100027")
        self.assertEqual(result[CONF_USERNAME], "user")


class TestGroupsSchema(unittest.TestCase):
    """Tests for the group filter step schema."""

    def test_filter_is_optional(self):
        """An empty filter is allowed and means all groups."""
        self.assertEqual(groups_schema()({})[CONF_GROUP_FILTER], "")

    def test_existing_filter_is_prefilled(self):
        """The current filter prefills the form."""
        schema = groups_schema({CONF_GROUP_FILTER: "G1,G2"})
        self.assertEqual(schema({})[CONF_GROUP_FILTER], "G1,G2")


if __name__ == "__main__":
    unittest.main()
