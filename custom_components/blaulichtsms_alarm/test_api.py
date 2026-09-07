"""Unit tests for the blaulichtSMS Alarm API client."""

import unittest
from datetime import UTC, datetime, timedelta, timezone

from .api import (
    extract_alarm_groups,
    STAGING_BASE_URL,
    AlarmApiClient,
    build_trigger_payload,
    format_api_datetime,
    redact_payload,
)
from .errors import BlaulichtSmsApiError, BlaulichtSmsAuthError


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


class _FakeResponse:
    """Minimal stand-in for an aiohttp response."""

    def __init__(self, body):
        """Store the canned body."""
        self._body = body

    async def __aenter__(self):
        """Enter the async context."""
        return self

    async def __aexit__(self, *exc_info):
        """Leave the async context."""
        return False

    def raise_for_status(self):
        """Successful responses never raise."""

    async def json(self):
        """Return the canned body."""
        return self._body


class _FakeSession:
    """Records the last request and returns a canned body."""

    def __init__(self, body):
        """Store the body every request answers with."""
        self.body = body
        self.calls = []

    def post(self, url, json=None, headers=None):
        """Record the call and hand back a fake response."""
        self.calls.append({"url": url, "json": json, "headers": headers})
        return _FakeResponse(self.body)


class TestAlarmApiClient(unittest.IsolatedAsyncioTestCase):
    """Tests for AlarmApiClient."""

    def _client(self, body, **kwargs):
        """Build a client backed by a fake session."""
        session = _FakeSession(body)
        client = AlarmApiClient(
            customer_id="100027",
            username="user",
            password="secret",
            session=session,
            **kwargs,
        )
        return client, session

    async def test_trigger_posts_to_the_live_url(self):
        """The trigger endpoint is called on the live base url by default."""
        client, session = self._client({"result": "OK", "alarmId": "abc"})
        await client.trigger(alarm_type="alarm", alarm_text="Test")
        self.assertEqual(
            session.calls[0]["url"],
            "https://api.blaulichtsms.net/blaulicht/api/alarm/v1/trigger",
        )
        self.assertEqual(session.calls[0]["json"]["alarmText"], "Test")

    async def test_staging_base_url(self):
        """A staging client posts to the staging host."""
        client, session = self._client({"result": "OK"}, base_url=STAGING_BASE_URL)
        await client.trigger(alarm_type="alarm")
        self.assertTrue(
            session.calls[0]["url"].startswith(
                "https://api-staging.blaulichtsms.net/blaulicht"
            )
        )

    async def test_trigger_returns_the_body(self):
        """A successful trigger returns the parsed body."""
        body = {"result": "OK", "alarmId": "abc", "alarmData": {"alarmId": "abc"}}
        client, _ = self._client(body)
        self.assertEqual(await client.trigger(alarm_type="alarm"), body)

    async def test_auth_result_raises_auth_error(self):
        """Credential related result codes raise BlaulichtSmsAuthError."""
        client, _ = self._client(
            {"result": "UNKNOWN_USER", "description": "no such user"}
        )
        with self.assertRaises(BlaulichtSmsAuthError) as ctx:
            await client.trigger(alarm_type="alarm")
        self.assertEqual(ctx.exception.result, "UNKNOWN_USER")

    async def test_not_configured_for_customer_raises_auth_error(self):
        """NOT_CONFIGURED_FOR_CUSTOMER is treated as an auth problem."""
        client, _ = self._client({"result": "NOT_CONFIGURED_FOR_CUSTOMER"})
        with self.assertRaises(BlaulichtSmsAuthError):
            await client.trigger(alarm_type="alarm")

    async def test_other_result_raises_api_error(self):
        """Any other non-OK result raises BlaulichtSmsApiError."""
        client, _ = self._client(
            {"result": "INVALID_GROUP", "description": "G9 unknown"}
        )
        with self.assertRaises(BlaulichtSmsApiError) as ctx:
            await client.trigger(alarm_type="alarm")
        self.assertEqual(ctx.exception.result, "INVALID_GROUP")
        self.assertNotIsInstance(ctx.exception, BlaulichtSmsAuthError)

    async def test_missing_result_raises_api_error(self):
        """A body without a result field is treated as an unknown error."""
        client, _ = self._client({})
        with self.assertRaises(BlaulichtSmsApiError) as ctx:
            await client.trigger(alarm_type="alarm")
        self.assertEqual(ctx.exception.result, "UNKNOWN_ERROR")

    async def test_query_sends_alarm_id(self):
        """Query posts credentials, customer id and alarm id."""
        client, session = self._client({"result": "OK", "alarmData": {"a": 1}})
        result = await client.query("abc")
        self.assertEqual(
            session.calls[0]["url"],
            "https://api.blaulichtsms.net/blaulicht/api/alarm/v1/query",
        )
        self.assertEqual(session.calls[0]["json"]["alarmId"], "abc")
        self.assertEqual(session.calls[0]["json"]["customerId"], "100027")
        self.assertEqual(result, {"a": 1})

    async def test_list_alarms_returns_the_alarm_list(self):
        """List returns the alarms array and sends customerIds as a list."""
        client, session = self._client({"result": "OK", "alarms": [{"a": 1}]})
        result = await client.list_alarms()
        self.assertEqual(session.calls[0]["json"]["customerIds"], ["100027"])
        self.assertNotIn("startDate", session.calls[0]["json"])
        self.assertEqual(result, [{"a": 1}])

    async def test_list_alarms_formats_the_date_range(self):
        """Start and end date are serialised in the API date format."""
        client, session = self._client({"result": "OK", "alarms": []})
        await client.list_alarms(
            start_date=datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
            end_date=datetime(2026, 1, 2, 0, 0, tzinfo=UTC),
        )
        self.assertEqual(
            session.calls[0]["json"]["startDate"], "2026-01-01T00:00:00.000Z"
        )
        self.assertEqual(
            session.calls[0]["json"]["endDate"], "2026-01-02T00:00:00.000Z"
        )


class TestExtractAlarmGroups(unittest.TestCase):
    """The alarm group inventory derived from a list response."""

    def test_returns_an_empty_mapping_for_no_alarms(self):
        """Without alarms there is nothing to suggest."""
        self.assertEqual(extract_alarm_groups([]), {})

    def test_maps_group_ids_to_group_names(self):
        """Each alarm group contributes its id and name."""
        alarms = [
            {"alarmGroups": [{"groupId": "G1", "groupName": "Gesamtwehr"}]},
        ]
        self.assertEqual(extract_alarm_groups(alarms), {"G1": "Gesamtwehr"})

    def test_deduplicates_groups_across_alarms(self):
        """A group alerted repeatedly is reported once."""
        alarms = [
            {"alarmGroups": [{"groupId": "G1", "groupName": "Gesamtwehr"}]},
            {"alarmGroups": [{"groupId": "G1", "groupName": "Gesamtwehr"}]},
        ]
        self.assertEqual(extract_alarm_groups(alarms), {"G1": "Gesamtwehr"})

    def test_sorts_numeric_group_codes_naturally(self):
        """G10 comes after G2, not after G1."""
        alarms = [
            {
                "alarmGroups": [
                    {"groupId": "G10", "groupName": "ten"},
                    {"groupId": "G2", "groupName": "two"},
                    {"groupId": "G1", "groupName": "one"},
                ]
            }
        ]
        self.assertEqual(list(extract_alarm_groups(alarms)), ["G1", "G2", "G10"])

    def test_sorts_non_numeric_codes_after_numeric_ones(self):
        """Codes that do not follow the G<number> scheme go last."""
        alarms = [
            {
                "alarmGroups": [
                    {"groupId": "SONDER", "groupName": "special"},
                    {"groupId": "G2", "groupName": "two"},
                ]
            }
        ]
        self.assertEqual(list(extract_alarm_groups(alarms)), ["G2", "SONDER"])

    def test_falls_back_to_the_group_id_when_the_name_is_missing(self):
        """A group without a name is still selectable."""
        alarms = [{"alarmGroups": [{"groupId": "G3", "groupName": None}]}]
        self.assertEqual(extract_alarm_groups(alarms), {"G3": "G3"})

    def test_ignores_alarms_and_groups_without_a_group_id(self):
        """Malformed entries never end up in the inventory."""
        alarms = [
            {"alarmGroups": None},
            {},
            {"alarmGroups": [{"groupName": "nameless"}, {"groupId": ""}]},
        ]
        self.assertEqual(extract_alarm_groups(alarms), {})


if __name__ == "__main__":
    unittest.main()
