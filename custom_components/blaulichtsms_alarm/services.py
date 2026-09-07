"""Services of the blaulichtSMS Alarm integration."""

from __future__ import annotations

import logging

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from .api import MAX_LIST_LIMIT
from .const import (
    ATTR_ADDITIONAL_MSISDNS,
    ATTR_ADDRESS,
    ATTR_ALARM_ID,
    ATTR_ALARM_TEXT,
    ATTR_CONFIG_ENTRY,
    ATTR_DURATION,
    ATTR_END_DATE,
    ATTR_GROUP_CODES,
    ATTR_HIDE_TRIGGER_DETAILS,
    ATTR_INDEX_NUMBER,
    ATTR_LIMIT,
    ATTR_LOCATION,
    ATTR_NEEDS_ACKNOWLEDGEMENT,
    ATTR_RECIPIENT_CONFIRMATION,
    ATTR_RECIPIENT_CONFIRMATION_TARGET,
    ATTR_START_DATE,
    ATTR_TEMPLATE,
    DOMAIN,
    SERVICE_CREATE_APPOINTMENT,
    SERVICE_LIST_ALARMS,
    SERVICE_QUERY_ALARM,
    SERVICE_SEND_INFO,
    SERVICE_TRIGGER_ALARM,
    SIGNAL_ALARM_TRIGGERED,
    TYPE_ALARM,
    TYPE_INFO,
)
from .errors import BlaulichtSmsApiError, BlaulichtSmsAuthError
from .group_filter import GroupNotAllowedError, GroupsRequiredError, resolve_group_codes

_LOGGER = logging.getLogger(__name__)

_TRIGGER_FIELDS = {
    vol.Optional(ATTR_CONFIG_ENTRY): cv.string,
    vol.Optional(ATTR_ALARM_TEXT): cv.string,
    vol.Optional(ATTR_GROUP_CODES): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(ATTR_NEEDS_ACKNOWLEDGEMENT, default=True): cv.boolean,
    vol.Optional(ATTR_DURATION): cv.positive_int,
    vol.Optional(ATTR_TEMPLATE): cv.string,
    vol.Optional(ATTR_INDEX_NUMBER): cv.positive_int,
    vol.Optional(ATTR_ADDITIONAL_MSISDNS): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(ATTR_HIDE_TRIGGER_DETAILS): cv.boolean,
    vol.Optional(ATTR_RECIPIENT_CONFIRMATION): cv.boolean,
    vol.Optional(ATTR_RECIPIENT_CONFIRMATION_TARGET): cv.string,
    vol.Optional(ATTR_LOCATION): vol.Schema(
        {
            vol.Required("latitude"): cv.latitude,
            vol.Required("longitude"): cv.longitude,
        },
        extra=vol.ALLOW_EXTRA,
    ),
    vol.Optional(ATTR_ADDRESS): cv.string,
}

TRIGGER_SCHEMA = vol.Schema(_TRIGGER_FIELDS)
APPOINTMENT_SCHEMA = vol.Schema(
    {**_TRIGGER_FIELDS, vol.Required(ATTR_START_DATE): cv.datetime}
)
QUERY_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY): cv.string,
        vol.Required(ATTR_ALARM_ID): cv.string,
    }
)
LIST_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY): cv.string,
        vol.Optional(ATTR_START_DATE): cv.datetime,
        vol.Optional(ATTR_END_DATE): cv.datetime,
        vol.Optional(ATTR_LIMIT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=MAX_LIST_LIMIT)
        ),
    }
)


def resolve_entry(hass: HomeAssistant, entry_id: str | None) -> ConfigEntry:
    """Return the loaded config entry a service call targets."""
    entries = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
    ]
    if entry_id is not None:
        for entry in entries:
            if entry.entry_id == entry_id:
                return entry
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="entry_not_found",
            translation_placeholders={"entry_id": entry_id},
        )
    if not entries:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="no_entry"
        )
    if len(entries) > 1:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="entry_required"
        )
    return entries[0]


def _resolve_groups(call: ServiceCall, group_filter: list[str]) -> list[str] | None:
    """Apply the group filter and translate its errors for the UI."""
    try:
        return resolve_group_codes(call.data.get(ATTR_GROUP_CODES), group_filter)
    except GroupsRequiredError as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="groups_required",
            translation_placeholders={"allowed": ", ".join(group_filter)},
        ) from err
    except GroupNotAllowedError as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="group_not_allowed",
            translation_placeholders={
                "groups": ", ".join(err.invalid),
                "allowed": ", ".join(group_filter),
            },
        ) from err


def _check_additional_msisdns(call: ServiceCall, group_filter: list[str]) -> None:
    """Reject direct numbers while a group filter is configured.

    Alerting single numbers would bypass the group restriction entirely.
    """
    if group_filter and call.data.get(ATTR_ADDITIONAL_MSISDNS):
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="msisdns_not_allowed"
        )


async def async_trigger(
    hass: HomeAssistant,
    call: ServiceCall,
    alarm_type: str,
    *,
    with_start_date: bool,
) -> ServiceResponse:
    """Trigger an alarm, an info or an appointment."""
    entry = resolve_entry(hass, call.data.get(ATTR_CONFIG_ENTRY))
    runtime = entry.runtime_data
    group_codes = _resolve_groups(call, runtime.group_filter)
    _check_additional_msisdns(call, runtime.group_filter)

    location = call.data.get(ATTR_LOCATION) or {}
    try:
        body = await runtime.client.trigger(
            alarm_type=alarm_type,
            alarm_text=call.data.get(ATTR_ALARM_TEXT),
            group_codes=group_codes,
            needs_acknowledgement=call.data.get(ATTR_NEEDS_ACKNOWLEDGEMENT, True),
            start_date=call.data.get(ATTR_START_DATE) if with_start_date else None,
            duration=call.data.get(ATTR_DURATION),
            template=call.data.get(ATTR_TEMPLATE),
            index_number=call.data.get(ATTR_INDEX_NUMBER),
            additional_msisdns=call.data.get(ATTR_ADDITIONAL_MSISDNS),
            hide_trigger_details=call.data.get(ATTR_HIDE_TRIGGER_DETAILS),
            recipient_confirmation=call.data.get(ATTR_RECIPIENT_CONFIRMATION),
            recipient_confirmation_target=call.data.get(
                ATTR_RECIPIENT_CONFIRMATION_TARGET
            ),
            latitude=location.get("latitude"),
            longitude=location.get("longitude"),
            address=call.data.get(ATTR_ADDRESS),
        )
    except BlaulichtSmsAuthError as err:
        entry.async_start_reauth(hass)
        raise HomeAssistantError(
            f"blaulichtSMS rejected the credentials: {err}"
        ) from err
    except BlaulichtSmsApiError as err:
        raise HomeAssistantError(f"blaulichtSMS returned an error: {err}") from err
    except aiohttp.ClientError as err:
        raise HomeAssistantError(f"could not reach blaulichtSMS: {err}") from err

    runtime.last_alarm = {
        "alarm_id": body.get("alarmId"),
        "alarm_text": call.data.get(ATTR_ALARM_TEXT),
        "type": alarm_type,
        "group_codes": group_codes or [],
        "result": body.get("result"),
        "triggered_at": dt_util.utcnow(),
    }
    async_dispatcher_send(hass, f"{SIGNAL_ALARM_TRIGGERED}_{entry.entry_id}")

    return {
        "alarm_id": body.get("alarmId"),
        "result": body.get("result"),
        "alarm_data": body.get("alarmData"),
    }


async def async_query_alarm(hass: HomeAssistant, call: ServiceCall) -> ServiceResponse:
    """Return the current data of a single alarm."""
    entry = resolve_entry(hass, call.data.get(ATTR_CONFIG_ENTRY))
    try:
        alarm_data = await entry.runtime_data.client.query(call.data[ATTR_ALARM_ID])
    except BlaulichtSmsAuthError as err:
        entry.async_start_reauth(hass)
        raise HomeAssistantError(
            f"blaulichtSMS rejected the credentials: {err}"
        ) from err
    except (BlaulichtSmsApiError, aiohttp.ClientError) as err:
        raise HomeAssistantError(f"blaulichtSMS query failed: {err}") from err
    return {"alarm_data": alarm_data}


async def async_list_alarms(hass: HomeAssistant, call: ServiceCall) -> ServiceResponse:
    """Return the alarms of the configured customer."""
    entry = resolve_entry(hass, call.data.get(ATTR_CONFIG_ENTRY))
    try:
        alarms = await entry.runtime_data.client.list_alarms(
            start_date=call.data.get(ATTR_START_DATE),
            end_date=call.data.get(ATTR_END_DATE),
            limit=call.data.get(ATTR_LIMIT),
        )
    except BlaulichtSmsAuthError as err:
        entry.async_start_reauth(hass)
        raise HomeAssistantError(
            f"blaulichtSMS rejected the credentials: {err}"
        ) from err
    except (BlaulichtSmsApiError, aiohttp.ClientError) as err:
        raise HomeAssistantError(f"blaulichtSMS list failed: {err}") from err
    return {"alarms": alarms}


@callback
def async_register_services(hass: HomeAssistant) -> None:
    """Register all blaulichtSMS Alarm services once."""
    if hass.services.has_service(DOMAIN, SERVICE_TRIGGER_ALARM):
        return

    async def _trigger_alarm(call: ServiceCall) -> ServiceResponse:
        return await async_trigger(hass, call, TYPE_ALARM, with_start_date=False)

    async def _send_info(call: ServiceCall) -> ServiceResponse:
        return await async_trigger(hass, call, TYPE_INFO, with_start_date=False)

    async def _create_appointment(call: ServiceCall) -> ServiceResponse:
        return await async_trigger(hass, call, TYPE_INFO, with_start_date=True)

    async def _query_alarm(call: ServiceCall) -> ServiceResponse:
        return await async_query_alarm(hass, call)

    async def _list_alarms(call: ServiceCall) -> ServiceResponse:
        return await async_list_alarms(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_TRIGGER_ALARM,
        _trigger_alarm,
        schema=TRIGGER_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_INFO,
        _send_info,
        schema=TRIGGER_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_APPOINTMENT,
        _create_appointment,
        schema=APPOINTMENT_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_QUERY_ALARM,
        _query_alarm,
        schema=QUERY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_LIST_ALARMS,
        _list_alarms,
        schema=LIST_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
