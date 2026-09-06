"""Unit tests for the blaulichtSMS Alarm API client."""

import unittest
from datetime import UTC, datetime, timedelta, timezone

from .api import build_trigger_payload, format_api_datetime, redact_payload


class TestFormatApiDatetime(unittest.TestCase):
    """Tests for format_api_datetime."""

    def test_utc_datetime(self):
        """A UTC datetime is rendered with a trailing Z and milliseconds."""
        value = datetime(2026, 10, 1, 16, 0, 0, tzinfo=UTC)
        self.assertEqual(format_api_datetime(value), "2026-10-01T16:00:00.000Z")

    def test_local_datetime_is_converted_to_utc(self):
        """A datetime with an offset is converted to UTC first."""
        value = datetime(2026, 10, 1, 18, 0, 0, tzinfo=timezone(timedelta(hours=2)))
        self.assertEqual(format_api_datetime(value), "2026-10-01T16:00:00.000Z")


class TestBuildTriggerPayload(unittest.TestCase):
    """Tests for build_trigger_payload."""

    def _payload(self, **kwargs):
        """Build a payload with the mandatory arguments filled in."""
        base = {
            "customer_id": "100027",
            "username": "user",
            "password": "secret",
            "alarm_type": "alarm",
        }
        return build_trigger_payload(**{**base, **kwargs})

    def test_mandatory_fields_are_present(self):
        """Credentials, customer, type and acknowledgement are always sent."""
        payload = self._payload()
        self.assertEqual(
            payload,
            {
                "username": "user",
                "password": "secret",
                "customerId": "100027",
                "type": "alarm",
                "needsAcknowledgement": True,
            },
        )

    def test_unset_optionals_are_omitted(self):
        """Optional fields that are None do not appear in the payload."""
        payload = self._payload(alarm_text=None, duration=None, template=None)
        self.assertNotIn("alarmText", payload)
        self.assertNotIn("duration", payload)
        self.assertNotIn("template", payload)

    def test_optional_fields_are_mapped_to_api_names(self):
        """Snake case arguments are mapped to the camel case API fields."""
        payload = self._payload(
            alarm_text="Brand B2",
            group_codes=["G1", "G2"],
            duration=60,
            template="A1",
            index_number=7,
            additional_msisdns=["+4366412345678"],
            hide_trigger_details=True,
            recipient_confirmation=False,
            recipient_confirmation_target="+4366412345678",
        )
        self.assertEqual(payload["alarmText"], "Brand B2")
        self.assertEqual(payload["groupCodes"], ["G1", "G2"])
        self.assertEqual(payload["duration"], 60)
        self.assertEqual(payload["template"], "A1")
        self.assertEqual(payload["indexNumber"], 7)
        self.assertEqual(payload["additionalMsisdns"], ["+4366412345678"])
        self.assertTrue(payload["hideTriggerDetails"])
        self.assertFalse(payload["recipientConfirmation"])
        self.assertEqual(payload["recipientConfirmationTarget"], "+4366412345678")

    def test_needs_acknowledgement_can_be_disabled(self):
        """needs_acknowledgement=False is sent as False, not dropped."""
        payload = self._payload(needs_acknowledgement=False)
        self.assertFalse(payload["needsAcknowledgement"])

    def test_start_date_is_formatted_as_utc(self):
        """A start date is serialised in the API date format."""
        payload = self._payload(
            alarm_type="info",
            start_date=datetime(2026, 10, 1, 16, 0, 0, tzinfo=UTC),
        )
        self.assertEqual(payload["startDate"], "2026-10-01T16:00:00.000Z")

    def test_coordinates_are_used_when_given(self):
        """Latitude and longitude become a coordinates object."""
        payload = self._payload(latitude=48.205587, longitude=16.342917)
        self.assertEqual(payload["coordinates"], {"lat": 48.205587, "lon": 16.342917})
        self.assertNotIn("geolocation", payload)

    def test_address_becomes_geolocation(self):
        """An address without coordinates becomes a geolocation object."""
        payload = self._payload(address="Getreidemarkt 11, 1060 Wien")
        self.assertEqual(
            payload["geolocation"], {"address": "Getreidemarkt 11, 1060 Wien"}
        )
        self.assertNotIn("coordinates", payload)

    def test_coordinates_win_over_address(self):
        """Coordinates take precedence and the address is dropped."""
        payload = self._payload(
            latitude=48.2, longitude=16.3, address="Getreidemarkt 11"
        )
        self.assertIn("coordinates", payload)
        self.assertNotIn("geolocation", payload)

    def test_partial_coordinates_fall_back_to_address(self):
        """A single coordinate is not enough and is ignored."""
        payload = self._payload(latitude=48.2, address="Getreidemarkt 11")
        self.assertNotIn("coordinates", payload)
        self.assertEqual(payload["geolocation"], {"address": "Getreidemarkt 11"})

    def test_empty_group_codes_are_omitted(self):
        """An empty group list is not sent so the API default applies."""
        payload = self._payload(group_codes=[])
        self.assertNotIn("groupCodes", payload)


class TestRedactPayload(unittest.TestCase):
    """Tests for redact_payload."""

    def test_password_is_masked(self):
        """The password never appears in a redacted payload."""
        redacted = redact_payload({"username": "user", "password": "secret"})
        self.assertEqual(redacted["password"], "***")
        self.assertEqual(redacted["username"], "user")

    def test_original_is_not_modified(self):
        """Redacting returns a copy and leaves the original intact."""
        payload = {"password": "secret"}
        redact_payload(payload)
        self.assertEqual(payload["password"], "secret")


if __name__ == "__main__":
    unittest.main()
