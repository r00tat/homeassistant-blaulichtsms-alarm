"""Unit tests for the blaulichtSMS Alarm services."""

import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .const import (
    ATTR_ADDITIONAL_MSISDNS,
    ATTR_ALARM_TEXT,
    ATTR_CONFIG_ENTRY,
    ATTR_GROUP_CODES,
    ATTR_LIMIT,
    ATTR_NEEDS_ACKNOWLEDGEMENT,
    ATTR_START_DATE,
    TYPE_ALARM,
    TYPE_INFO,
)
from .errors import BlaulichtSmsApiError, BlaulichtSmsAuthError
from .services import (
    LIST_SCHEMA,
    async_list_alarms,
    async_query_alarm,
    async_trigger,
    resolve_entry,
)

_MODULE = "custom_components.blaulichtsms_alarm.services"


def _entry(
    entry_id="entry-1", group_filter=None, trigger_result=None, side_effect=None
):
    """Build a stub config entry with a fake client in runtime_data."""
    client = MagicMock()
    client.trigger = AsyncMock(
        return_value=trigger_result
        or {"result": "OK", "alarmId": "abc", "alarmData": {"alarmId": "abc"}},
        side_effect=side_effect,
    )
    client.query = AsyncMock(return_value={"alarmId": "abc"})
    client.list_alarms = AsyncMock(return_value=[{"alarmId": "abc"}])
    return SimpleNamespace(
        entry_id=entry_id,
        state=ConfigEntryState.LOADED,
        runtime_data=SimpleNamespace(
            client=client, group_filter=group_filter or [], last_alarm=None
        ),
        async_start_reauth=MagicMock(),
    )


def _hass(*entries):
    """Build a hass stub that reports the given config entries."""
    hass = MagicMock()
    hass.config_entries.async_entries.return_value = list(entries)
    return hass


def _call(**data):
    """Build a stub service call."""
    return SimpleNamespace(data=data)


class TestResolveEntry(unittest.TestCase):
    """Tests for resolve_entry."""

    def test_single_entry_is_resolved_without_an_id(self):
        """With one entry the config_entry field may be omitted."""
        entry = _entry()
        self.assertIs(resolve_entry(_hass(entry), None), entry)

    def test_no_entry_raises(self):
        """Without a configured entry the service cannot run."""
        with self.assertRaises(ServiceValidationError):
            resolve_entry(_hass(), None)

    def test_several_entries_require_an_id(self):
        """With more than one entry the caller must pick one."""
        with self.assertRaises(ServiceValidationError):
            resolve_entry(_hass(_entry("a"), _entry("b")), None)

    def test_entry_is_selected_by_id(self):
        """A given id selects the matching entry."""
        first, second = _entry("a"), _entry("b")
        self.assertIs(resolve_entry(_hass(first, second), "b"), second)

    def test_unknown_id_raises(self):
        """An unknown id is a user error."""
        with self.assertRaises(ServiceValidationError):
            resolve_entry(_hass(_entry("a")), "nope")

    def test_unloaded_entries_are_ignored(self):
        """Entries that failed to set up are not selectable."""
        entry = _entry()
        entry.state = ConfigEntryState.SETUP_ERROR
        with self.assertRaises(ServiceValidationError):
            resolve_entry(_hass(entry), None)


class TestTrigger(unittest.IsolatedAsyncioTestCase):
    """Tests for the three triggering services."""

    async def _trigger(self, entry, call, alarm_type=TYPE_ALARM, with_start_date=False):
        """Run async_trigger with the dispatcher patched out."""
        with patch(f"{_MODULE}.async_dispatcher_send") as dispatch:
            result = await async_trigger(
                _hass(entry), call, alarm_type, with_start_date=with_start_date
            )
        return result, dispatch

    async def test_alarm_sends_type_alarm(self):
        """trigger_alarm sends type alarm and no start date."""
        entry = _entry()
        await self._trigger(
            entry,
            _call(**{ATTR_ALARM_TEXT: "Brand B2", ATTR_NEEDS_ACKNOWLEDGEMENT: True}),
        )
        kwargs = entry.runtime_data.client.trigger.await_args.kwargs
        self.assertEqual(kwargs["alarm_type"], TYPE_ALARM)
        self.assertIsNone(kwargs["start_date"])
        self.assertEqual(kwargs["alarm_text"], "Brand B2")

    async def test_info_sends_type_info(self):
        """send_info sends type info and no start date."""
        entry = _entry()
        await self._trigger(entry, _call(), alarm_type=TYPE_INFO)
        kwargs = entry.runtime_data.client.trigger.await_args.kwargs
        self.assertEqual(kwargs["alarm_type"], TYPE_INFO)
        self.assertIsNone(kwargs["start_date"])

    async def test_appointment_sends_the_start_date(self):
        """create_appointment forwards the start date."""
        entry = _entry()
        start = datetime(2026, 10, 1, 16, 0, tzinfo=UTC)
        await self._trigger(
            entry,
            _call(**{ATTR_START_DATE: start}),
            alarm_type=TYPE_INFO,
            with_start_date=True,
        )
        kwargs = entry.runtime_data.client.trigger.await_args.kwargs
        self.assertEqual(kwargs["alarm_type"], TYPE_INFO)
        self.assertEqual(kwargs["start_date"], start)

    async def test_response_contains_alarm_id_and_data(self):
        """The service response exposes alarm id, result and alarm data."""
        result, _ = await self._trigger(_entry(), _call())
        self.assertEqual(
            result,
            {"alarm_id": "abc", "result": "OK", "alarm_data": {"alarmId": "abc"}},
        )

    async def test_last_alarm_is_recorded_and_dispatched(self):
        """A successful trigger updates runtime data and notifies the sensor."""
        entry = _entry()
        _, dispatch = await self._trigger(entry, _call(**{ATTR_ALARM_TEXT: "Brand B2"}))
        last = entry.runtime_data.last_alarm
        self.assertEqual(last["alarm_id"], "abc")
        self.assertEqual(last["alarm_text"], "Brand B2")
        self.assertEqual(last["type"], TYPE_ALARM)
        self.assertIsNotNone(last["triggered_at"])
        dispatch.assert_called_once()

    async def test_allowed_group_is_forwarded(self):
        """A group inside the filter reaches the API."""
        entry = _entry(group_filter=["G1", "G2"])
        await self._trigger(entry, _call(**{ATTR_GROUP_CODES: ["G1"]}))
        self.assertEqual(
            entry.runtime_data.client.trigger.await_args.kwargs["group_codes"], ["G1"]
        )

    async def test_disallowed_group_aborts_without_calling_the_api(self):
        """A group outside the filter raises and triggers nothing."""
        entry = _entry(group_filter=["G1"])
        with self.assertRaises(ServiceValidationError):
            await self._trigger(entry, _call(**{ATTR_GROUP_CODES: ["G3"]}))
        entry.runtime_data.client.trigger.assert_not_awaited()

    async def test_missing_groups_abort_when_a_filter_is_set(self):
        """Without groups and with a filter the call is rejected."""
        entry = _entry(group_filter=["G1"])
        with self.assertRaises(ServiceValidationError):
            await self._trigger(entry, _call())
        entry.runtime_data.client.trigger.assert_not_awaited()

    async def test_without_filter_no_groups_are_allowed(self):
        """Without a filter an empty group list reaches the API as None."""
        entry = _entry()
        await self._trigger(entry, _call())
        self.assertIsNone(
            entry.runtime_data.client.trigger.await_args.kwargs["group_codes"]
        )

    async def test_additional_msisdns_are_blocked_with_a_filter(self):
        """Direct numbers would bypass the filter and are rejected."""
        entry = _entry(group_filter=["G1"])
        with self.assertRaises(ServiceValidationError):
            await self._trigger(
                entry,
                _call(
                    **{
                        ATTR_GROUP_CODES: ["G1"],
                        ATTR_ADDITIONAL_MSISDNS: ["+4366412345678"],
                    }
                ),
            )
        entry.runtime_data.client.trigger.assert_not_awaited()

    async def test_additional_msisdns_are_allowed_without_a_filter(self):
        """Without a filter direct numbers are forwarded."""
        entry = _entry()
        await self._trigger(
            entry, _call(**{ATTR_ADDITIONAL_MSISDNS: ["+4366412345678"]})
        )
        self.assertEqual(
            entry.runtime_data.client.trigger.await_args.kwargs["additional_msisdns"],
            ["+4366412345678"],
        )

    async def test_auth_error_starts_reauth(self):
        """An auth error surfaces as an error and starts the reauth flow."""
        entry = _entry(side_effect=BlaulichtSmsAuthError("UNKNOWN_USER"))
        with self.assertRaises(HomeAssistantError):
            await self._trigger(entry, _call())
        entry.async_start_reauth.assert_called_once()

    async def test_api_error_becomes_a_home_assistant_error(self):
        """An API error is reported with its result code."""
        entry = _entry(side_effect=BlaulichtSmsApiError("INVALID_TEMPLATE", "no A9"))
        with self.assertRaises(HomeAssistantError) as ctx:
            await self._trigger(entry, _call())
        self.assertIn("INVALID_TEMPLATE", str(ctx.exception))

    async def test_network_error_becomes_a_home_assistant_error(self):
        """A network failure is reported as an error."""
        entry = _entry(side_effect=aiohttp.ClientError("boom"))
        with self.assertRaises(HomeAssistantError):
            await self._trigger(entry, _call())


class TestQueryAndList(unittest.IsolatedAsyncioTestCase):
    """Tests for the read-only services."""

    async def test_query_returns_alarm_data(self):
        """query_alarm returns the alarm data under alarm_data."""
        entry = _entry()
        result = await async_query_alarm(_hass(entry), _call(alarm_id="abc"))
        self.assertEqual(result, {"alarm_data": {"alarmId": "abc"}})
        entry.runtime_data.client.query.assert_awaited_once_with("abc")

    async def test_list_returns_alarms(self):
        """list_alarms returns the alarms under alarms."""
        entry = _entry()
        result = await async_list_alarms(_hass(entry), _call())
        self.assertEqual(result, {"alarms": [{"alarmId": "abc"}]})

    async def test_list_forwards_the_date_range(self):
        """Start and end date are handed to the client."""
        entry = _entry()
        start = datetime(2026, 1, 1, tzinfo=UTC)
        end = datetime(2026, 1, 2, tzinfo=UTC)
        await async_list_alarms(_hass(entry), _call(start_date=start, end_date=end))
        entry.runtime_data.client.list_alarms.assert_awaited_once_with(
            start_date=start, end_date=end, limit=None
        )

    async def test_list_forwards_the_limit(self):
        """The limit field is handed to the client."""
        entry = _entry()
        await async_list_alarms(_hass(entry), _call(limit=5))
        entry.runtime_data.client.list_alarms.assert_awaited_once_with(
            start_date=None, end_date=None, limit=5
        )

    async def test_query_uses_the_selected_entry(self):
        """The config_entry field selects the account to query."""
        first, second = _entry("a"), _entry("b")
        await async_query_alarm(
            _hass(first, second), _call(alarm_id="abc", **{ATTR_CONFIG_ENTRY: "b"})
        )
        second.runtime_data.client.query.assert_awaited_once()
        first.runtime_data.client.query.assert_not_awaited()


class TestListSchema(unittest.TestCase):
    """Validation of the list_alarms service fields."""

    def test_accepts_a_limit_within_the_api_cap(self):
        """The API never returns more than 100 alarms."""
        self.assertEqual(LIST_SCHEMA({ATTR_LIMIT: 100})[ATTR_LIMIT], 100)

    def test_rejects_a_limit_above_the_api_cap(self):
        """A limit that cannot be honoured is refused up front."""
        with self.assertRaises(vol.Invalid):
            LIST_SCHEMA({ATTR_LIMIT: 101})

    def test_rejects_a_limit_below_one(self):
        """Asking for no alarms at all is pointless."""
        with self.assertRaises(vol.Invalid):
            LIST_SCHEMA({ATTR_LIMIT: 0})

    def test_the_limit_is_optional(self):
        """Without a limit the full response is returned."""
        self.assertNotIn(ATTR_LIMIT, LIST_SCHEMA({}))


if __name__ == "__main__":
    unittest.main()
