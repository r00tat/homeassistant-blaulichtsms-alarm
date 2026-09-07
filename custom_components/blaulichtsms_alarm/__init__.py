"""The blaulichtSMS Alarm integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import LIVE_BASE_URL, STAGING_BASE_URL, AlarmApiClient
from .const import (
    CONF_CUSTOMER_ID,
    CONF_GROUP_FILTER,
    CONF_PASSWORD,
    CONF_USE_STAGING,
    CONF_USERNAME,
    PLATFORMS,
)
from .errors import BlaulichtSmsApiError, BlaulichtSmsAuthError
from .group_filter import parse_group_filter
from .services import async_register_services


@dataclass
class BlaulichtSmsAlarmRuntimeData:
    """State a loaded config entry keeps in memory."""

    client: AlarmApiClient
    group_filter: list[str]
    last_alarm: dict[str, Any] | None = None


type BlaulichtSmsAlarmConfigEntry = ConfigEntry[BlaulichtSmsAlarmRuntimeData]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the services once, independent of any config entry."""
    async_register_services(hass)
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: BlaulichtSmsAlarmConfigEntry
) -> bool:
    """Set up one blaulichtSMS alarm account."""
    options = {**entry.data, **entry.options}
    client = AlarmApiClient(
        customer_id=options[CONF_CUSTOMER_ID],
        username=options[CONF_USERNAME],
        password=options[CONF_PASSWORD],
        base_url=STAGING_BASE_URL if options.get(CONF_USE_STAGING) else LIVE_BASE_URL,
        session=async_get_clientsession(hass),
    )

    try:
        await client.list_alarms()
    except BlaulichtSmsAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except (BlaulichtSmsApiError, aiohttp.ClientError) as err:
        raise ConfigEntryNotReady(str(err)) from err

    entry.runtime_data = BlaulichtSmsAlarmRuntimeData(
        client=client,
        group_filter=parse_group_filter(options.get(CONF_GROUP_FILTER)),
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: BlaulichtSmsAlarmConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(
    hass: HomeAssistant, entry: BlaulichtSmsAlarmConfigEntry
) -> None:
    """Reload the entry when its data or options changed."""
    await hass.config_entries.async_reload(entry.entry_id)
