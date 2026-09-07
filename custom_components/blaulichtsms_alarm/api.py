"""Client for the blaulichtSMS Alarm API v1.

See https://github.com/blaulichtSMS/docs/blob/master/alarm_api_v1.md
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

import aiohttp

from .errors import BlaulichtSmsApiError, BlaulichtSmsAuthError

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


AUTH_RESULT_CODES = frozenset(
    {
        "UNKNOWN_USER",
        "NOT_AUTHORIZED",
        "NOT_CONFIGURED_FOR_CUSTOMER",
        "INVALID_CUSTOMER_ID",
        "DEACTIVATED",
    }
)

TRIGGER_PATH = "/api/alarm/v1/trigger"
QUERY_PATH = "/api/alarm/v1/query"
LIST_PATH = "/api/alarm/v1/list"


_GROUP_CODE_RE = re.compile(r"^G(\d+)$")


def _group_sort_key(code: str) -> tuple[int, int, str]:
    """Sort G<number> codes numerically and everything else after them."""
    if match := _GROUP_CODE_RE.match(code):
        return (0, int(match.group(1)), "")
    return (1, 0, code)


def extract_alarm_groups(alarms: list[dict[str, Any]]) -> dict[str, str]:
    """Return the alarm groups seen in a list response, id mapped to name.

    The alarm API has no endpoint that lists the configured alarm groups, so
    the inventory is derived from the groups of the returned alarms. It is
    therefore a suggestion, not the full truth: a group that was not alerted
    recently does not show up.
    """
    groups: dict[str, str] = {}
    for alarm in alarms:
        for group in alarm.get("alarmGroups") or []:
            code = (group.get("groupId") or "").strip()
            if not code:
                continue
            groups.setdefault(code, (group.get("groupName") or "").strip() or code)
    return {code: groups[code] for code in sorted(groups, key=_group_sort_key)}


class AlarmApiClient:
    """Async client for the blaulichtSMS Alarm API.

    The alarm API has no login endpoint: credentials are sent with every
    request.
    """

    def __init__(
        self,
        customer_id: str,
        username: str,
        password: str,
        base_url: str = LIVE_BASE_URL,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Create a client for one customer id."""
        self.customer_id = customer_id
        self.username = username
        self.password = password
        self.base_url = base_url.rstrip("/")
        self._session = session

    @property
    def _credentials(self) -> dict[str, Any]:
        """Return the credential fields every request carries."""
        return {"username": self.username, "password": self.password}

    async def trigger(self, **kwargs: Any) -> dict[str, Any]:
        """Trigger an alarm or info and return the API response body."""
        payload = build_trigger_payload(
            customer_id=self.customer_id,
            username=self.username,
            password=self.password,
            **kwargs,
        )
        return await self._post(TRIGGER_PATH, payload)

    async def query(self, alarm_id: str) -> dict[str, Any]:
        """Return the alarm data for a single alarm id."""
        payload = {
            **self._credentials,
            "customerId": self.customer_id,
            "alarmId": alarm_id,
        }
        body = await self._post(QUERY_PATH, payload)
        return body.get("alarmData") or {}

    async def list_alarms(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Return up to 100 alarms, optionally limited to a date range."""
        payload: dict[str, Any] = {
            **self._credentials,
            "customerIds": [self.customer_id],
        }
        if start_date is not None:
            payload["startDate"] = format_api_datetime(start_date)
        if end_date is not None:
            payload["endDate"] = format_api_datetime(end_date)
        body = await self._post(LIST_PATH, payload)
        return body.get("alarms") or []

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST a payload and return the checked response body."""
        url = f"{self.base_url}{path}"
        _LOGGER.debug("POST %s %s", url, redact_payload(payload))
        if self._session is None:
            async with aiohttp.ClientSession() as owned:
                body = await self._request(owned, url, payload)
        else:
            body = await self._request(self._session, url, payload)
        return self._check_result(body)

    @staticmethod
    async def _request(
        session: aiohttp.ClientSession, url: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Perform the POST and return the parsed JSON body."""
        async with session.post(
            url, json=payload, headers={"Content-Type": "application/json"}
        ) as response:
            response.raise_for_status()
            return await response.json()

    @staticmethod
    def _check_result(body: dict[str, Any]) -> dict[str, Any]:
        """Raise on a non-OK result code, otherwise return the body."""
        result = body.get("result")
        if result == "OK":
            return body
        description = body.get("description")
        if result in AUTH_RESULT_CODES:
            raise BlaulichtSmsAuthError(result, description)
        raise BlaulichtSmsApiError(result or "UNKNOWN_ERROR", description)
