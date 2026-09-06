"""Client for the blaulichtSMS Alarm API v1.

See https://github.com/blaulichtSMS/docs/blob/master/alarm_api_v1.md
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

LIVE_BASE_URL = "https://api.blaulichtsms.net/blaulicht"
STAGING_BASE_URL = "https://api-staging.blaulichtsms.net/blaulicht"

_LOGGER = logging.getLogger(__name__)

_OPTIONAL_FIELDS = {
    "alarm_text": "alarmText",
    "duration": "duration",
    "template": "template",
    "index_number": "indexNumber",
    "hide_trigger_details": "hideTriggerDetails",
    "recipient_confirmation": "recipientConfirmation",
    "recipient_confirmation_target": "recipientConfirmationTarget",
}


def format_api_datetime(value: datetime) -> str:
    """Format a datetime as the UTC string the alarm API expects."""
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow copy of a request payload with the password masked."""
    redacted = dict(payload)
    if "password" in redacted:
        redacted["password"] = "***"
    return redacted


def build_trigger_payload(
    *,
    customer_id: str,
    username: str,
    password: str,
    alarm_type: str,
    needs_acknowledgement: bool = True,
    alarm_text: str | None = None,
    group_codes: list[str] | None = None,
    start_date: datetime | None = None,
    duration: int | None = None,
    template: str | None = None,
    index_number: int | None = None,
    additional_msisdns: list[str] | None = None,
    hide_trigger_details: bool | None = None,
    recipient_confirmation: bool | None = None,
    recipient_confirmation_target: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    address: str | None = None,
) -> dict[str, Any]:
    """Build the JSON payload for the trigger endpoint.

    Fields that are None are omitted so the API defaults apply. Coordinates take
    precedence over an address; if both are given the address is dropped.
    """
    payload: dict[str, Any] = {
        "username": username,
        "password": password,
        "customerId": customer_id,
        "type": alarm_type,
        "needsAcknowledgement": needs_acknowledgement,
    }

    arguments = locals()
    for argument, api_field in _OPTIONAL_FIELDS.items():
        if arguments[argument] is not None:
            payload[api_field] = arguments[argument]

    if group_codes:
        payload["groupCodes"] = list(group_codes)
    if additional_msisdns:
        payload["additionalMsisdns"] = list(additional_msisdns)
    if start_date is not None:
        payload["startDate"] = format_api_datetime(start_date)

    if latitude is not None and longitude is not None:
        payload["coordinates"] = {"lat": latitude, "lon": longitude}
        if address:
            _LOGGER.warning(
                "both coordinates and an address were given; ignoring the address"
            )
    elif address:
        payload["geolocation"] = {"address": address}

    return payload
