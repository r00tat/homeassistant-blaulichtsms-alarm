"""Config flow for the blaulichtSMS Alarm integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import aiohttp

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LIVE_BASE_URL, STAGING_BASE_URL, AlarmApiClient
from .const import (
    CONF_CUSTOMER_ID,
    CONF_PASSWORD,
    CONF_USE_STAGING,
    CONF_USERNAME,
    DOMAIN,
)
from .errors import BlaulichtSmsApiError, BlaulichtSmsAuthError
from .schema import (
    build_title,
    build_unique_id,
    groups_schema,
    reauth_schema,
    user_schema,
)

_LOGGER = logging.getLogger(__name__)


async def validate_credentials(
    hass: HomeAssistant, data: Mapping[str, Any]
) -> dict[str, str]:
    """Check credentials with a read-only list call.

    Returns a dict of form errors, empty when the credentials work. The list
    endpoint is used on purpose: it never triggers an alarm.
    """
    client = AlarmApiClient(
        customer_id=data[CONF_CUSTOMER_ID],
        username=data[CONF_USERNAME],
        password=data[CONF_PASSWORD],
        base_url=STAGING_BASE_URL if data.get(CONF_USE_STAGING) else LIVE_BASE_URL,
        session=async_get_clientsession(hass),
    )
    try:
        await client.list_alarms()
    except BlaulichtSmsAuthError:
        _LOGGER.warning("blaulichtSMS alarm api rejected the credentials")
        return {"base": "invalid_auth"}
    except aiohttp.ClientError:
        _LOGGER.exception("could not reach the blaulichtSMS alarm api")
        return {"base": "cannot_connect"}
    except BlaulichtSmsApiError:
        _LOGGER.exception("blaulichtSMS alarm api returned an error")
        return {"base": "unknown"}
    return {}


class BlaulichtSmsAlarmConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Two step setup wizard for the blaulichtSMS Alarm integration."""

    VERSION = 1

    def __init__(self) -> None:
        """Start with an empty set of collected data."""
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect and verify the alarm api credentials."""
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(
                build_unique_id(
                    user_input[CONF_CUSTOMER_ID],
                    bool(user_input.get(CONF_USE_STAGING)),
                )
            )
            self._abort_if_unique_id_configured()
            errors = await validate_credentials(self.hass, user_input)
            if not errors:
                self._data = dict(user_input)
                return await self.async_step_groups()

        return self.async_show_form(
            step_id="user", data_schema=user_schema(user_input), errors=errors
        )

    async def async_step_groups(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect the optional alarm group filter and create the entry."""
        if user_input is not None:
            return self.async_create_entry(
                title=build_title(
                    self._data[CONF_CUSTOMER_ID],
                    bool(self._data.get(CONF_USE_STAGING)),
                ),
                data={**self._data, **user_input},
            )
        return self.async_show_form(step_id="groups", data_schema=groups_schema())

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start a reauth flow."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for new credentials for an existing entry."""
        return await self._async_update_credentials(
            self._get_reauth_entry(), "reauth_confirm", "reauth_successful", user_input
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user change the credentials of an existing entry."""
        return await self._async_update_credentials(
            self._get_reconfigure_entry(),
            "reconfigure",
            "reconfigure_successful",
            user_input,
        )

    async def _async_update_credentials(
        self,
        entry: config_entries.ConfigEntry,
        step_id: str,
        abort_reason: str,
        user_input: dict[str, Any] | None,
    ) -> ConfigFlowResult:
        """Validate and store new credentials for an existing entry.

        Updating the entry fires the update listener registered in
        async_setup_entry, which reloads the integration, so no explicit reload
        is issued here.
        """
        errors: dict[str, str] = {}
        if user_input is not None:
            merged = {**entry.data, **user_input}
            errors = await validate_credentials(self.hass, merged)
            if not errors:
                self.hass.config_entries.async_update_entry(entry, data=merged)
                return self.async_abort(reason=abort_reason)

        return self.async_show_form(
            step_id=step_id, data_schema=reauth_schema(entry.data), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return BlaulichtSmsAlarmOptionsFlow()


class BlaulichtSmsAlarmOptionsFlow(config_entries.OptionsFlow):
    """Options flow that changes the alarm group filter."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the group filter."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        defaults = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init", data_schema=groups_schema(defaults)
        )
