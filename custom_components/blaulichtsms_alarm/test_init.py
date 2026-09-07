"""Unit tests for the integration setup."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp

from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from . import async_setup_entry
from .const import (
    CONF_CUSTOMER_ID,
    CONF_GROUP_FILTER,
    CONF_PASSWORD,
    CONF_USE_STAGING,
    CONF_USERNAME,
)
from .errors import BlaulichtSmsApiError, BlaulichtSmsAuthError

_DATA = {
    CONF_CUSTOMER_ID: "100027",
    CONF_USERNAME: "user",
    CONF_PASSWORD: "secret",
    CONF_USE_STAGING: False,
    CONF_GROUP_FILTER: "G1, G2",
}

_MODULE = "custom_components.blaulichtsms_alarm"


class TestAsyncSetupEntry(unittest.IsolatedAsyncioTestCase):
    """Tests for async_setup_entry."""

    def _entry(self, **overrides):
        """Build a stub config entry."""
        entry = MagicMock()
        entry.data = {**_DATA, **overrides}
        entry.options = {}
        entry.entry_id = "entry-1"
        entry.runtime_data = None
        return entry

    async def _setup(self, entry, side_effect=None):
        """Run async_setup_entry against a patched client."""
        client = MagicMock()
        client.list_alarms = AsyncMock(return_value=[], side_effect=side_effect)
        hass = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()
        with (
            patch(f"{_MODULE}.AlarmApiClient", return_value=client) as factory,
            patch(f"{_MODULE}.async_get_clientsession"),
        ):
            result = await async_setup_entry(hass, entry)
        return result, factory, hass

    async def test_successful_setup_stores_runtime_data(self):
        """A working entry ends up with a client and a parsed group filter."""
        entry = self._entry()
        result, _, hass = await self._setup(entry)
        self.assertTrue(result)
        self.assertEqual(entry.runtime_data.group_filter, ["G1", "G2"])
        self.assertIsNone(entry.runtime_data.last_alarm)
        hass.config_entries.async_forward_entry_setups.assert_awaited_once()

    async def test_empty_group_filter_allows_all_groups(self):
        """Without a filter the runtime data holds an empty list."""
        entry = self._entry(**{CONF_GROUP_FILTER: ""})
        await self._setup(entry)
        self.assertEqual(entry.runtime_data.group_filter, [])

    async def test_live_url_is_used_by_default(self):
        """A live entry talks to the production host."""
        _, factory, _ = await self._setup(self._entry())
        self.assertIn("api.blaulichtsms.net", factory.call_args.kwargs["base_url"])

    async def test_staging_url_is_used_when_configured(self):
        """A staging entry talks to the test host."""
        _, factory, _ = await self._setup(self._entry(**{CONF_USE_STAGING: True}))
        self.assertIn(
            "api-staging.blaulichtsms.net", factory.call_args.kwargs["base_url"]
        )

    async def test_options_override_data(self):
        """A group filter set in the options wins over the one in data."""
        entry = self._entry()
        entry.options = {CONF_GROUP_FILTER: "G9"}
        await self._setup(entry)
        self.assertEqual(entry.runtime_data.group_filter, ["G9"])

    async def test_auth_error_raises_config_entry_auth_failed(self):
        """Bad credentials ask Home Assistant for a reauth."""
        with self.assertRaises(ConfigEntryAuthFailed):
            await self._setup(self._entry(), BlaulichtSmsAuthError("UNKNOWN_USER"))

    async def test_network_error_raises_not_ready(self):
        """A network failure makes Home Assistant retry later."""
        with self.assertRaises(ConfigEntryNotReady):
            await self._setup(self._entry(), aiohttp.ClientError("boom"))

    async def test_api_error_raises_not_ready(self):
        """A transient API error makes Home Assistant retry later."""
        with self.assertRaises(ConfigEntryNotReady):
            await self._setup(self._entry(), BlaulichtSmsApiError("UNKNOWN_ERROR"))


if __name__ == "__main__":
    unittest.main()
