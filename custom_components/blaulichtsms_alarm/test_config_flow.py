"""Unit tests for the blaulichtSMS Alarm config flow."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp

from .config_flow import (
    BlaulichtSmsAlarmConfigFlow,
    BlaulichtSmsAlarmOptionsFlow,
    CredentialCheck,
    validate_credentials,
)
from .const import (
    CONF_CUSTOMER_ID,
    CONF_GROUP_FILTER,
    CONF_PASSWORD,
    CONF_USE_STAGING,
    CONF_USERNAME,
)
from .errors import BlaulichtSmsApiError, BlaulichtSmsAuthError

_CREDENTIALS = {
    CONF_CUSTOMER_ID: "100027",
    CONF_USERNAME: "user",
    CONF_PASSWORD: "secret",
    CONF_USE_STAGING: False,
}

_MODULE = "custom_components.blaulichtsms_alarm.config_flow"


class TestValidateCredentials(unittest.IsolatedAsyncioTestCase):
    """Tests for validate_credentials."""

    async def _validate(self, side_effect=None, alarms=None):
        """Run validate_credentials against a patched client."""
        client = MagicMock()
        client.list_alarms = AsyncMock(
            side_effect=side_effect, return_value=alarms or []
        )
        with (
            patch(f"{_MODULE}.AlarmApiClient", return_value=client),
            patch(f"{_MODULE}.async_get_clientsession"),
        ):
            check = await validate_credentials(MagicMock(), _CREDENTIALS)
        return check.errors, client, check.groups

    async def test_valid_credentials_produce_no_errors(self):
        """A successful list call means the credentials are good."""
        errors, client, _ = await self._validate()
        self.assertEqual(errors, {})
        client.list_alarms.assert_awaited_once()

    async def test_the_alarm_groups_are_taken_from_the_list_response(self):
        """The credential check doubles as the group discovery."""
        _, _, groups = await self._validate(
            alarms=[{"alarmGroups": [{"groupId": "G1", "groupName": "Gesamtwehr"}]}]
        )
        self.assertEqual(groups, {"G1": "Gesamtwehr"})

    async def test_no_groups_are_reported_when_the_check_fails(self):
        """A failed check cannot have discovered anything."""
        _, _, groups = await self._validate(BlaulichtSmsAuthError("UNKNOWN_USER"))
        self.assertEqual(groups, {})

    async def test_auth_error_maps_to_invalid_auth(self):
        """An auth error is reported on the form as invalid_auth."""
        errors, _, _ = await self._validate(BlaulichtSmsAuthError("UNKNOWN_USER"))
        self.assertEqual(errors, {"base": "invalid_auth"})

    async def test_client_error_maps_to_cannot_connect(self):
        """A network failure is reported as cannot_connect."""
        errors, _, _ = await self._validate(aiohttp.ClientError("boom"))
        self.assertEqual(errors, {"base": "cannot_connect"})

    async def test_other_api_error_maps_to_unknown(self):
        """Any other API error is reported as unknown."""
        errors, _, _ = await self._validate(BlaulichtSmsApiError("UNKNOWN_ERROR"))
        self.assertEqual(errors, {"base": "unknown"})

    async def test_staging_flag_selects_the_staging_url(self):
        """use_staging switches the client to the staging base url."""
        client = MagicMock()
        client.list_alarms = AsyncMock(return_value=[])
        with (
            patch(f"{_MODULE}.AlarmApiClient", return_value=client) as factory,
            patch(f"{_MODULE}.async_get_clientsession"),
        ):
            await validate_credentials(
                MagicMock(), {**_CREDENTIALS, CONF_USE_STAGING: True}
            )
        self.assertIn("api-staging", factory.call_args.kwargs["base_url"])


class TestConfigFlowSteps(unittest.IsolatedAsyncioTestCase):
    """Tests for the two wizard steps."""

    def _flow(self):
        """Build a flow with hass and unique id handling stubbed out."""
        flow = BlaulichtSmsAlarmConfigFlow()
        flow.hass = MagicMock()
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()
        return flow

    async def test_first_step_shows_the_credentials_form(self):
        """Without input the credentials form is shown."""
        result = await self._flow().async_step_user(None)
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "user")

    async def test_invalid_credentials_redisplay_the_form(self):
        """Bad credentials keep the user on the first step."""
        flow = self._flow()
        with patch(
            f"{_MODULE}.validate_credentials",
            AsyncMock(return_value=CredentialCheck({"base": "invalid_auth"}, {})),
        ):
            result = await flow.async_step_user(dict(_CREDENTIALS))
        self.assertEqual(result["step_id"], "user")
        self.assertEqual(result["errors"], {"base": "invalid_auth"})

    async def test_valid_credentials_advance_to_the_groups_step(self):
        """Good credentials lead to the group filter step."""
        flow = self._flow()
        with patch(
            f"{_MODULE}.validate_credentials",
            AsyncMock(return_value=CredentialCheck({}, {})),
        ):
            result = await flow.async_step_user(dict(_CREDENTIALS))
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "groups")

    async def test_groups_step_creates_the_entry(self):
        """The second step creates the entry with credentials and filter."""
        flow = self._flow()
        flow._data = dict(_CREDENTIALS)
        result = await flow.async_step_groups({CONF_GROUP_FILTER: ["G1", "G2"]})
        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["title"], "blaulichtSMS Alarm 100027")
        self.assertEqual(result["data"][CONF_GROUP_FILTER], ["G1", "G2"])
        self.assertEqual(result["data"][CONF_CUSTOMER_ID], "100027")

    async def test_the_groups_step_offers_the_discovered_groups(self):
        """The groups found during the credential check become options."""
        flow = self._flow()
        with patch(
            f"{_MODULE}.validate_credentials",
            AsyncMock(return_value=CredentialCheck({}, {"G1": "Gesamtwehr"})),
        ):
            result = await flow.async_step_user(dict(_CREDENTIALS))
        selector = result["data_schema"].schema[CONF_GROUP_FILTER]
        self.assertEqual(
            selector.config["options"],
            [{"value": "G1", "label": "G1 \u2013 Gesamtwehr"}],
        )

    async def test_unique_id_is_set_from_customer_and_environment(self):
        """The unique id combines environment and customer id."""
        flow = self._flow()
        with patch(
            f"{_MODULE}.validate_credentials",
            AsyncMock(return_value=CredentialCheck({}, {})),
        ):
            await flow.async_step_user({**_CREDENTIALS, CONF_USE_STAGING: True})
        flow.async_set_unique_id.assert_awaited_once_with("staging-100027")


class TestOptionsFlowGroupDiscovery(unittest.IsolatedAsyncioTestCase):
    """The options flow offers the same group suggestions."""

    def _flow(self, client):
        """Build an options flow bound to an entry with the given client."""
        entry = MagicMock()
        entry.data = dict(_CREDENTIALS)
        entry.options = {}
        entry.runtime_data = MagicMock(client=client)
        return BlaulichtSmsAlarmOptionsFlow(), entry

    async def test_offers_groups_from_the_running_client(self):
        """The already configured client is reused to discover groups."""
        client = MagicMock()
        client.list_alarms = AsyncMock(
            return_value=[{"alarmGroups": [{"groupId": "G2", "groupName": "AS"}]}]
        )
        flow, entry = self._flow(client)
        with patch.object(
            BlaulichtSmsAlarmOptionsFlow, "config_entry", entry, create=True
        ):
            result = await flow.async_step_init(None)
        selector = result["data_schema"].schema[CONF_GROUP_FILTER]
        self.assertEqual(
            selector.config["options"], [{"value": "G2", "label": "G2 \u2013 AS"}]
        )

    async def test_a_failing_discovery_still_shows_the_form(self):
        """An unreachable API must not block editing the filter."""
        client = MagicMock()
        client.list_alarms = AsyncMock(side_effect=aiohttp.ClientError("boom"))
        flow, entry = self._flow(client)
        with patch.object(
            BlaulichtSmsAlarmOptionsFlow, "config_entry", entry, create=True
        ):
            result = await flow.async_step_init(None)
        self.assertEqual(result["type"], "form")
        selector = result["data_schema"].schema[CONF_GROUP_FILTER]
        self.assertEqual(selector.config["options"], [])


if __name__ == "__main__":
    unittest.main()
