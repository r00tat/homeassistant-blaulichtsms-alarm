# blaulichtSMS Alarm Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eine Home-Assistant-Custom-Integration `blaulichtsms_alarm`, mit der aus Automatisierungen heraus blaulichtSMS-Alarme, -Infos und -Termine ausgelöst und abgefragt werden können.

**Architecture:** Config-Entry-only Integration mit HA-freiem `aiohttp`-Client (`api.py`), einer reinen Filter-Funktion (`group_filter.py`) und fünf Services (`services.py`), die zwischen beidem übersetzen. Der Zustand liegt in `entry.runtime_data`; ein Sensor zeigt die letzte Auslösung und wird per Dispatcher aktualisiert.

**Tech Stack:** Python 3.14, Home Assistant, `aiohttp`, `voluptuous`, `unittest` (kein Netzwerk in Tests), `uv`, `ruff`, release-please, HACS.

**Spec:** [docs/superpowers/specs/2026-09-06-blaulichtsms-alarm-design.md](../specs/2026-09-06-blaulichtsms-alarm-design.md)

---

## Dateistruktur

| Datei | Verantwortung |
| --- | --- |
| `custom_components/__init__.py` | leer, macht `custom_components` importierbar |
| `custom_components/blaulichtsms_alarm/const.py` | `DOMAIN`, `CONF_*`, `ATTR_*`, `SERVICE_*`, `SIGNAL_*`, `VERSION` |
| `custom_components/blaulichtsms_alarm/errors.py` | Exception-Hierarchie des API-Clients |
| `custom_components/blaulichtsms_alarm/api.py` | `AlarmApiClient` + Payload-Builder, keine HA-Importe |
| `custom_components/blaulichtsms_alarm/group_filter.py` | Parsen und Durchsetzen des Gruppen-Filters, reine Funktionen |
| `custom_components/blaulichtsms_alarm/schema.py` | voluptuous-Schemas der Config-Flow-Schritte |
| `custom_components/blaulichtsms_alarm/config_flow.py` | Wizard, Options-, Reauth-, Reconfigure-Flow |
| `custom_components/blaulichtsms_alarm/__init__.py` | `RuntimeData`, Setup/Unload, Service-Registrierung |
| `custom_components/blaulichtsms_alarm/services.py` | Service-Schemas und -Handler |
| `custom_components/blaulichtsms_alarm/services.yaml` | Felddefinitionen für die HA-Service-UI |
| `custom_components/blaulichtsms_alarm/sensor.py` | Sensor "letzter ausgelöster Alarm" |
| `custom_components/blaulichtsms_alarm/manifest.json` | Metadaten, einzige Quelle der Versionsnummer |
| `custom_components/blaulichtsms_alarm/strings.json` + `translations/{de,en}.json` | UI-Texte |
| `custom_components/blaulichtsms_alarm/test_*.py` | unittest, neben dem Code |

**Testkonvention:** Wie im bestehenden `blaulichtsms`-Plugin laufen alle Tests mit `unittest` ohne HA-Test-Harness. `hass` wird mit `MagicMock` gestellt, Async-Tests erben von `unittest.IsolatedAsyncioTestCase`. Kein Test darf ins Netz gehen.

---

### Task 1: Projektgerüst und Werkzeuge

**Files:**
- Create: `custom_components/__init__.py`
- Create: `custom_components/blaulichtsms_alarm/__init__.py` (vorerst leer)
- Create: `custom_components/blaulichtsms_alarm/manifest.json`
- Create: `custom_components/blaulichtsms_alarm/const.py`
- Create: `hacs.json`, `.ruff.toml`, `requirements.txt`, `dev.sh`
- Create: `release-please-config.json`, `.release-please-manifest.json`

- [ ] **Step 1: Verzeichnisse und leere Pakete anlegen**

```bash
mkdir -p custom_components/blaulichtsms_alarm/translations
touch custom_components/__init__.py custom_components/blaulichtsms_alarm/__init__.py
```

- [ ] **Step 2: `manifest.json` schreiben**

```json
{
  "domain": "blaulichtsms_alarm",
  "name": "blaulichtSMS Alarm",
  "documentation": "https://github.com/r00tat/homeassistant-blaulichtsms-alarm",
  "issue_tracker": "https://github.com/r00tat/homeassistant-blaulichtsms-alarm/issues",
  "dependencies": [],
  "requirements": [],
  "config_flow": true,
  "iot_class": "cloud_push",
  "integration_type": "service",
  "codeowners": [
    "@r00tat"
  ],
  "version": "0.1.0"
}
```

- [ ] **Step 3: `const.py` schreiben**

```python
"""Constants for the blaulichtSMS Alarm integration."""

import json
from pathlib import Path

DOMAIN = "blaulichtsms_alarm"

CONF_CUSTOMER_ID = "customer_id"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_USE_STAGING = "use_staging"
CONF_GROUP_FILTER = "group_filter"

SERVICE_TRIGGER_ALARM = "trigger_alarm"
SERVICE_SEND_INFO = "send_info"
SERVICE_CREATE_APPOINTMENT = "create_appointment"
SERVICE_QUERY_ALARM = "query_alarm"
SERVICE_LIST_ALARMS = "list_alarms"

ATTR_CONFIG_ENTRY = "config_entry"
ATTR_ALARM_TEXT = "alarm_text"
ATTR_GROUP_CODES = "group_codes"
ATTR_NEEDS_ACKNOWLEDGEMENT = "needs_acknowledgement"
ATTR_DURATION = "duration"
ATTR_TEMPLATE = "template"
ATTR_INDEX_NUMBER = "index_number"
ATTR_ADDITIONAL_MSISDNS = "additional_msisdns"
ATTR_HIDE_TRIGGER_DETAILS = "hide_trigger_details"
ATTR_RECIPIENT_CONFIRMATION = "recipient_confirmation"
ATTR_RECIPIENT_CONFIRMATION_TARGET = "recipient_confirmation_target"
ATTR_LOCATION = "location"
ATTR_ADDRESS = "address"
ATTR_START_DATE = "start_date"
ATTR_END_DATE = "end_date"
ATTR_ALARM_ID = "alarm_id"

TYPE_ALARM = "alarm"
TYPE_INFO = "info"

SIGNAL_ALARM_TRIGGERED = f"{DOMAIN}_alarm_triggered"

PLATFORMS = ["sensor"]

VERSION = json.loads((Path(__file__).parent / "manifest.json").read_text())["version"]
```

- [ ] **Step 4: `hacs.json` schreiben**

```json
{
  "name": "blaulichtSMS Alarm",
  "render_readme": true,
  "iot_class": "cloud_push"
}
```

- [ ] **Step 5: `.ruff.toml` aus dem bestehenden Plugin kopieren**

```bash
cp /Users/paul/Documents/developing/hassio/blaulichtsms/.ruff.toml .ruff.toml
```

- [ ] **Step 6: `requirements.txt` schreiben**

```
aiodns>=4.0.4
aiohttp>=3.14.3
homeassistant>=2026.9.0
ruff~=0.16.3
```

- [ ] **Step 7: `dev.sh` schreiben und ausführbar machen**

```bash
#!/bin/bash
# setup dev environment
set -eo pipefail

if [[ -z "$(which uv)" ]]; then
  echo "uv required!"
  echo "see https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

if [[ ! -d ".venv" ]]; then
  uv venv
  uv pip install -r requirements.txt
fi

mkdir -p config

rsync -avz custom_components/blaulichtsms_alarm/ config/custom_components/blaulichtsms_alarm/

if [ ! "$(docker ps -a -q -f name=homeassistant)" ]; then
  docker run -d \
    --name homeassistant \
    --privileged \
    --restart=unless-stopped \
    -e TZ=Europe/Vienna \
    -v $PWD/config:/config \
    -v /run/dbus:/run/dbus:ro \
    -p 8123:8123 \
    ghcr.io/home-assistant/home-assistant:stable
else
  docker restart homeassistant
fi
docker logs -n 10 -f homeassistant
```

Danach: `chmod +x dev.sh`

- [ ] **Step 8: release-please konfigurieren**

`release-please-config.json`:

```json
{
  "$schema": "https://raw.githubusercontent.com/googleapis/release-please/main/schemas/config.json",
  "release-type": "simple",
  "include-v-in-tag": false,
  "include-component-in-tag": false,
  "packages": {
    ".": {
      "package-name": "blaulichtsms-alarm",
      "changelog-path": "CHANGELOG.md",
      "extra-files": [
        {
          "type": "json",
          "path": "custom_components/blaulichtsms_alarm/manifest.json",
          "jsonpath": "$.version"
        }
      ],
      "changelog-sections": [
        { "type": "feat", "section": "Features" },
        { "type": "fix", "section": "Bug Fixes" },
        { "type": "perf", "section": "Performance Improvements" },
        { "type": "refactor", "section": "Code Refactoring" },
        { "type": "docs", "section": "Documentation" },
        { "type": "revert", "section": "Reverts" },
        { "type": "chore", "section": "Miscellaneous Chores", "hidden": true },
        { "type": "test", "section": "Tests", "hidden": true },
        { "type": "ci", "section": "Continuous Integration", "hidden": true },
        { "type": "build", "section": "Build System", "hidden": true },
        { "type": "style", "section": "Styles", "hidden": true }
      ]
    }
  }
}
```

`.release-please-manifest.json`:

```json
{
  ".": "0.1.0"
}
```

- [ ] **Step 9: Umgebung aufsetzen und Import prüfen**

Run:
```bash
uv venv && uv pip install -r requirements.txt
uv run python -c "import custom_components.blaulichtsms_alarm.const as c; print(c.DOMAIN, c.VERSION)"
```
Expected: `blaulichtsms_alarm 0.1.0`

- [ ] **Step 10: Commit**

```bash
git add custom_components hacs.json .ruff.toml requirements.txt dev.sh release-please-config.json .release-please-manifest.json
git commit -m "build: Projektgerüst für die blaulichtSMS Alarm Integration"
```

---

### Task 2: Exception-Hierarchie

**Files:**
- Create: `custom_components/blaulichtsms_alarm/errors.py`
- Test: `custom_components/blaulichtsms_alarm/test_errors.py`

- [ ] **Step 1: Write the failing test**

`custom_components/blaulichtsms_alarm/test_errors.py`:

```python
"""Unit tests for the API exception hierarchy."""

import unittest

from .errors import BlaulichtSmsApiError, BlaulichtSmsAuthError, BlaulichtSmsError


class TestErrors(unittest.TestCase):
    """Tests for the exception hierarchy."""

    def test_api_error_keeps_result_and_description(self):
        """The API error exposes result code and description."""
        err = BlaulichtSmsApiError("INVALID_GROUP", "group G9 unknown")
        self.assertEqual(err.result, "INVALID_GROUP")
        self.assertEqual(err.description, "group G9 unknown")
        self.assertEqual(str(err), "INVALID_GROUP: group G9 unknown")

    def test_api_error_without_description(self):
        """A missing description leaves the message at the result code."""
        err = BlaulichtSmsApiError("UNKNOWN_ERROR")
        self.assertIsNone(err.description)
        self.assertEqual(str(err), "UNKNOWN_ERROR")

    def test_auth_error_is_an_api_error(self):
        """Auth errors can be caught as API errors and as base errors."""
        err = BlaulichtSmsAuthError("UNKNOWN_USER", "no such user")
        self.assertIsInstance(err, BlaulichtSmsApiError)
        self.assertIsInstance(err, BlaulichtSmsError)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest custom_components.blaulichtsms_alarm.test_errors -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'custom_components.blaulichtsms_alarm.errors'`

- [ ] **Step 3: Write minimal implementation**

`custom_components/blaulichtsms_alarm/errors.py`:

```python
"""Exceptions raised by the blaulichtSMS Alarm API client."""


class BlaulichtSmsError(Exception):
    """Base class for all blaulichtSMS Alarm API errors."""


class BlaulichtSmsApiError(BlaulichtSmsError):
    """The API answered with a result code other than OK."""

    def __init__(self, result: str, description: str | None = None) -> None:
        """Store the API result code and its description."""
        self.result = result
        self.description = description
        super().__init__(f"{result}: {description}" if description else result)


class BlaulichtSmsAuthError(BlaulichtSmsApiError):
    """The API rejected the credentials or the customer configuration."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest custom_components.blaulichtsms_alarm.test_errors -v`
Expected: PASS, 3 Tests

- [ ] **Step 5: Commit**

```bash
git add custom_components/blaulichtsms_alarm/errors.py custom_components/blaulichtsms_alarm/test_errors.py
git commit -m "feat: Exception-Hierarchie für den Alarm API Client"
```

---

### Task 3: Payload-Builder des API-Clients

Der Builder ist eine reine Funktion und damit ohne HTTP testbar. Er entscheidet, welche Felder in den Request wandern.

**Files:**
- Create: `custom_components/blaulichtsms_alarm/api.py`
- Test: `custom_components/blaulichtsms_alarm/test_api.py`

- [ ] **Step 1: Write the failing test**

`custom_components/blaulichtsms_alarm/test_api.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest custom_components.blaulichtsms_alarm.test_api -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'custom_components.blaulichtsms_alarm.api'`

- [ ] **Step 3: Write minimal implementation**

`custom_components/blaulichtsms_alarm/api.py`:

```python
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

    local = locals()
    for argument, api_field in _OPTIONAL_FIELDS.items():
        if local[argument] is not None:
            payload[api_field] = local[argument]

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest custom_components.blaulichtsms_alarm.test_api -v`
Expected: PASS, 14 Tests

- [ ] **Step 5: Lint**

Run: `uv run python -m ruff check`
Expected: `All checks passed!`

- [ ] **Step 6: Commit**

```bash
git add custom_components/blaulichtsms_alarm/api.py custom_components/blaulichtsms_alarm/test_api.py
git commit -m "feat: Payload-Builder für den Alarm API Trigger-Endpunkt"
```

---

### Task 4: HTTP-Client und Auswertung der Result-Codes

**Files:**
- Modify: `custom_components/blaulichtsms_alarm/api.py`
- Modify: `custom_components/blaulichtsms_alarm/test_api.py`

- [ ] **Step 1: Write the failing test**

An `test_api.py` anhängen (die Importzeile oben um `AlarmApiClient` und die Fehler ergänzen):

```python
class _FakeResponse:
    """Minimal stand-in for an aiohttp response."""

    def __init__(self, body):
        self._body = body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    def raise_for_status(self):
        """Successful responses never raise."""

    async def json(self):
        """Return the canned body."""
        return self._body


class _FakeSession:
    """Records the last request and returns a canned body."""

    def __init__(self, body):
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
        client, session = self._client(
            {"result": "OK"}, base_url=STAGING_BASE_URL
        )
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
```

Die Importzeile am Kopf der Datei wird zu:

```python
from .api import (
    STAGING_BASE_URL,
    AlarmApiClient,
    build_trigger_payload,
    format_api_datetime,
    redact_payload,
)
from .errors import BlaulichtSmsApiError, BlaulichtSmsAuthError
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest custom_components.blaulichtsms_alarm.test_api -v`
Expected: FAIL — `ImportError: cannot import name 'AlarmApiClient'`

- [ ] **Step 3: Write minimal implementation**

An `api.py` anhängen und den Kopf um `import aiohttp` sowie die Fehler-Importe ergänzen:

```python
import aiohttp

from .errors import BlaulichtSmsApiError, BlaulichtSmsAuthError

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest custom_components.blaulichtsms_alarm.test_api -v`
Expected: PASS, 24 Tests

- [ ] **Step 5: Lint und Commit**

```bash
uv run python -m ruff check
git add custom_components/blaulichtsms_alarm/api.py custom_components/blaulichtsms_alarm/test_api.py
git commit -m "feat: HTTP-Client für trigger, query und list"
```

---

### Task 5: Gruppen-Filter

**Files:**
- Create: `custom_components/blaulichtsms_alarm/group_filter.py`
- Test: `custom_components/blaulichtsms_alarm/test_group_filter.py`

- [ ] **Step 1: Write the failing test**

`custom_components/blaulichtsms_alarm/test_group_filter.py`:

```python
"""Unit tests for the alarm group filter."""

import unittest

from .group_filter import (
    GroupNotAllowedError,
    GroupsRequiredError,
    parse_group_filter,
    resolve_group_codes,
)


class TestParseGroupFilter(unittest.TestCase):
    """Tests for parse_group_filter."""

    def test_none_is_an_empty_filter(self):
        """No configured filter parses to an empty list."""
        self.assertEqual(parse_group_filter(None), [])

    def test_empty_string_is_an_empty_filter(self):
        """An empty string parses to an empty list."""
        self.assertEqual(parse_group_filter("   "), [])

    def test_comma_separated_codes_are_split_and_trimmed(self):
        """Codes are split on commas and surrounding spaces are removed."""
        self.assertEqual(parse_group_filter(" G1 , G2,G3 "), ["G1", "G2", "G3"])

    def test_empty_entries_are_dropped(self):
        """Stray commas do not create empty codes."""
        self.assertEqual(parse_group_filter("G1,,G2,"), ["G1", "G2"])


class TestResolveGroupCodes(unittest.TestCase):
    """Tests for resolve_group_codes."""

    def test_without_filter_requested_codes_pass_through(self):
        """With no filter the requested codes are returned unchanged."""
        self.assertEqual(resolve_group_codes(["G1", "G9"], []), ["G1", "G9"])

    def test_without_filter_empty_request_returns_none(self):
        """With no filter and no request the API default applies."""
        self.assertIsNone(resolve_group_codes(None, []))
        self.assertIsNone(resolve_group_codes([], []))

    def test_allowed_codes_are_returned(self):
        """A subset of the filter is accepted."""
        self.assertEqual(resolve_group_codes(["G1"], ["G1", "G2"]), ["G1"])

    def test_disallowed_code_raises(self):
        """A code outside the filter aborts the call."""
        with self.assertRaises(GroupNotAllowedError) as ctx:
            resolve_group_codes(["G1", "G3"], ["G1", "G2"])
        self.assertEqual(ctx.exception.invalid, ["G3"])

    def test_all_disallowed_codes_are_reported(self):
        """Every offending code is listed in the error."""
        with self.assertRaises(GroupNotAllowedError) as ctx:
            resolve_group_codes(["G3", "G4"], ["G1"])
        self.assertEqual(ctx.exception.invalid, ["G3", "G4"])

    def test_empty_request_with_filter_raises(self):
        """With a filter set the caller must name the groups explicitly."""
        with self.assertRaises(GroupsRequiredError):
            resolve_group_codes(None, ["G1"])
        with self.assertRaises(GroupsRequiredError):
            resolve_group_codes([], ["G1"])

    def test_requested_codes_are_trimmed(self):
        """Surrounding whitespace in a request is ignored."""
        self.assertEqual(resolve_group_codes([" G1 "], ["G1"]), ["G1"])

    def test_comparison_is_case_sensitive(self):
        """Group codes are compared case sensitively."""
        with self.assertRaises(GroupNotAllowedError):
            resolve_group_codes(["g1"], ["G1"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest custom_components.blaulichtsms_alarm.test_group_filter -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'custom_components.blaulichtsms_alarm.group_filter'`

- [ ] **Step 3: Write minimal implementation**

`custom_components/blaulichtsms_alarm/group_filter.py`:

```python
"""Parsing and enforcement of the optional alarm group filter."""

from __future__ import annotations


class GroupFilterError(Exception):
    """Base class for violations of the configured group filter."""


class GroupsRequiredError(GroupFilterError):
    """No group codes were given although a filter is configured."""

    def __init__(self) -> None:
        """Describe the missing group codes."""
        super().__init__("group codes are required while a group filter is set")


class GroupNotAllowedError(GroupFilterError):
    """Group codes outside of the configured filter were requested."""

    def __init__(self, invalid: list[str]) -> None:
        """Store the offending group codes."""
        self.invalid = invalid
        super().__init__(f"group codes not allowed: {', '.join(invalid)}")


def parse_group_filter(raw: str | None) -> list[str]:
    """Split a comma separated group filter into a list of group codes."""
    if not raw:
        return []
    return [code.strip() for code in raw.split(",") if code.strip()]


def resolve_group_codes(
    requested: list[str] | None, allowed: list[str] | None
) -> list[str] | None:
    """Validate requested group codes against the configured filter.

    Returns the group codes to send, or None when the API default should
    apply. Raises when the filter is set and the request violates it.
    """
    cleaned = [code.strip() for code in (requested or []) if code.strip()]
    if not allowed:
        return cleaned or None
    if not cleaned:
        raise GroupsRequiredError
    if invalid := [code for code in cleaned if code not in allowed]:
        raise GroupNotAllowedError(invalid)
    return cleaned
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest custom_components.blaulichtsms_alarm.test_group_filter -v`
Expected: PASS, 12 Tests

- [ ] **Step 5: Lint und Commit**

```bash
uv run python -m ruff check
git add custom_components/blaulichtsms_alarm/group_filter.py custom_components/blaulichtsms_alarm/test_group_filter.py
git commit -m "feat: strikte Durchsetzung des Alarmgruppen-Filters"
```

---

### Task 6: Config-Flow-Schemas und Hilfsfunktionen

Die Nicht-UI-Logik des Wizards wird als reine Funktionen ausgelagert, damit sie ohne HA-Test-Harness prüfbar ist.

**Files:**
- Create: `custom_components/blaulichtsms_alarm/schema.py`
- Test: `custom_components/blaulichtsms_alarm/test_schema.py`

- [ ] **Step 1: Write the failing test**

`custom_components/blaulichtsms_alarm/test_schema.py`:

```python
"""Unit tests for the config flow schemas and helpers."""

import unittest

from .const import (
    CONF_CUSTOMER_ID,
    CONF_GROUP_FILTER,
    CONF_PASSWORD,
    CONF_USE_STAGING,
    CONF_USERNAME,
)
from .schema import build_title, build_unique_id, groups_schema, user_schema


class TestUniqueId(unittest.TestCase):
    """Tests for build_unique_id."""

    def test_live_prefix(self):
        """A live entry is prefixed with live."""
        self.assertEqual(build_unique_id("100027", False), "live-100027")

    def test_staging_prefix(self):
        """A staging entry is prefixed with staging."""
        self.assertEqual(build_unique_id("100027", True), "staging-100027")


class TestTitle(unittest.TestCase):
    """Tests for build_title."""

    def test_live_title(self):
        """A live entry is titled with the customer id."""
        self.assertEqual(build_title("100027", False), "blaulichtSMS Alarm 100027")

    def test_staging_title_is_marked(self):
        """A staging entry is marked as a test account."""
        self.assertEqual(
            build_title("100027", True), "blaulichtSMS Alarm 100027 (Test)"
        )


class TestUserSchema(unittest.TestCase):
    """Tests for the credentials step schema."""

    def test_defaults_use_staging_to_false(self):
        """use_staging defaults to the live API."""
        result = user_schema()(
            {
                CONF_CUSTOMER_ID: "100027",
                CONF_USERNAME: "user",
                CONF_PASSWORD: "secret",
            }
        )
        self.assertFalse(result[CONF_USE_STAGING])

    def test_password_is_required(self):
        """A missing password is rejected."""
        with self.assertRaises(Exception):
            user_schema()({CONF_CUSTOMER_ID: "100027", CONF_USERNAME: "user"})

    def test_prefilled_defaults_are_used(self):
        """Existing values prefill the form."""
        schema = user_schema({CONF_CUSTOMER_ID: "100027", CONF_USERNAME: "user"})
        result = schema({CONF_PASSWORD: "secret"})
        self.assertEqual(result[CONF_CUSTOMER_ID], "100027")
        self.assertEqual(result[CONF_USERNAME], "user")


class TestGroupsSchema(unittest.TestCase):
    """Tests for the group filter step schema."""

    def test_filter_is_optional(self):
        """An empty filter is allowed and means all groups."""
        self.assertEqual(groups_schema()({})[CONF_GROUP_FILTER], "")

    def test_existing_filter_is_prefilled(self):
        """The current filter prefills the form."""
        schema = groups_schema({CONF_GROUP_FILTER: "G1,G2"})
        self.assertEqual(schema({})[CONF_GROUP_FILTER], "G1,G2")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest custom_components.blaulichtsms_alarm.test_schema -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'custom_components.blaulichtsms_alarm.schema'`

- [ ] **Step 3: Write minimal implementation**

`custom_components/blaulichtsms_alarm/schema.py`:

```python
"""Schemas and helpers for the blaulichtSMS Alarm config flow."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_CUSTOMER_ID,
    CONF_GROUP_FILTER,
    CONF_PASSWORD,
    CONF_USE_STAGING,
    CONF_USERNAME,
)


def build_unique_id(customer_id: str, use_staging: bool) -> str:
    """Return the unique id of a config entry.

    The environment is part of the id so a test and a live account for the same
    customer can be configured side by side.
    """
    return f"{'staging' if use_staging else 'live'}-{customer_id}"


def build_title(customer_id: str, use_staging: bool) -> str:
    """Return the title shown for a config entry."""
    suffix = " (Test)" if use_staging else ""
    return f"blaulichtSMS Alarm {customer_id}{suffix}"


def user_schema(data: dict[str, Any] | None = None) -> vol.Schema:
    """Return the schema of the credentials step."""
    data = data or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_CUSTOMER_ID, default=data.get(CONF_CUSTOMER_ID, "")
            ): cv.string,
            vol.Required(
                CONF_USERNAME, default=data.get(CONF_USERNAME, "")
            ): cv.string,
            vol.Required(CONF_PASSWORD): cv.string,
            vol.Optional(
                CONF_USE_STAGING, default=data.get(CONF_USE_STAGING, False)
            ): cv.boolean,
        }
    )


def groups_schema(data: dict[str, Any] | None = None) -> vol.Schema:
    """Return the schema of the group filter step."""
    data = data or {}
    return vol.Schema(
        {
            vol.Optional(
                CONF_GROUP_FILTER, default=data.get(CONF_GROUP_FILTER, "") or ""
            ): cv.string,
        }
    )


def reauth_schema(data: dict[str, Any] | None = None) -> vol.Schema:
    """Return the schema of the reauth step."""
    data = data or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_USERNAME, default=data.get(CONF_USERNAME, "")
            ): cv.string,
            vol.Required(CONF_PASSWORD): cv.string,
        }
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest custom_components.blaulichtsms_alarm.test_schema -v`
Expected: PASS, 8 Tests

- [ ] **Step 5: Commit**

```bash
git add custom_components/blaulichtsms_alarm/schema.py custom_components/blaulichtsms_alarm/test_schema.py
git commit -m "feat: Schemas und Helfer für den Einrichtungs-Wizard"
```

---

### Task 7: Config Flow — Wizard, Options, Reauth, Reconfigure

**Files:**
- Create: `custom_components/blaulichtsms_alarm/config_flow.py`
- Test: `custom_components/blaulichtsms_alarm/test_config_flow.py`

- [ ] **Step 1: Write the failing test**

`custom_components/blaulichtsms_alarm/test_config_flow.py`:

```python
"""Unit tests for the blaulichtSMS Alarm config flow."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp

from .config_flow import BlaulichtSmsAlarmConfigFlow, validate_credentials
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


class TestValidateCredentials(unittest.IsolatedAsyncioTestCase):
    """Tests for validate_credentials."""

    async def _validate(self, side_effect=None):
        """Run validate_credentials against a patched client."""
        client = MagicMock()
        client.list_alarms = AsyncMock(side_effect=side_effect, return_value=[])
        with (
            patch(
                "custom_components.blaulichtsms_alarm.config_flow.AlarmApiClient",
                return_value=client,
            ),
            patch(
                "custom_components.blaulichtsms_alarm.config_flow.async_get_clientsession"
            ),
        ):
            errors = await validate_credentials(MagicMock(), _CREDENTIALS)
        return errors, client

    async def test_valid_credentials_produce_no_errors(self):
        """A successful list call means the credentials are good."""
        errors, client = await self._validate()
        self.assertEqual(errors, {})
        client.list_alarms.assert_awaited_once()

    async def test_auth_error_maps_to_invalid_auth(self):
        """An auth error is reported on the form as invalid_auth."""
        errors, _ = await self._validate(BlaulichtSmsAuthError("UNKNOWN_USER"))
        self.assertEqual(errors, {"base": "invalid_auth"})

    async def test_client_error_maps_to_cannot_connect(self):
        """A network failure is reported as cannot_connect."""
        errors, _ = await self._validate(aiohttp.ClientError("boom"))
        self.assertEqual(errors, {"base": "cannot_connect"})

    async def test_other_api_error_maps_to_unknown(self):
        """Any other API error is reported as unknown."""
        errors, _ = await self._validate(BlaulichtSmsApiError("UNKNOWN_ERROR"))
        self.assertEqual(errors, {"base": "unknown"})

    async def test_staging_flag_selects_the_staging_url(self):
        """use_staging switches the client to the staging base url."""
        client = MagicMock()
        client.list_alarms = AsyncMock(return_value=[])
        with (
            patch(
                "custom_components.blaulichtsms_alarm.config_flow.AlarmApiClient",
                return_value=client,
            ) as factory,
            patch(
                "custom_components.blaulichtsms_alarm.config_flow.async_get_clientsession"
            ),
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
            "custom_components.blaulichtsms_alarm.config_flow.validate_credentials",
            AsyncMock(return_value={"base": "invalid_auth"}),
        ):
            result = await flow.async_step_user(dict(_CREDENTIALS))
        self.assertEqual(result["step_id"], "user")
        self.assertEqual(result["errors"], {"base": "invalid_auth"})

    async def test_valid_credentials_advance_to_the_groups_step(self):
        """Good credentials lead to the group filter step."""
        flow = self._flow()
        with patch(
            "custom_components.blaulichtsms_alarm.config_flow.validate_credentials",
            AsyncMock(return_value={}),
        ):
            result = await flow.async_step_user(dict(_CREDENTIALS))
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "groups")

    async def test_groups_step_creates_the_entry(self):
        """The second step creates the entry with credentials and filter."""
        flow = self._flow()
        flow._data = dict(_CREDENTIALS)
        result = await flow.async_step_groups({CONF_GROUP_FILTER: "G1,G2"})
        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["title"], "blaulichtSMS Alarm 100027")
        self.assertEqual(result["data"][CONF_GROUP_FILTER], "G1,G2")
        self.assertEqual(result["data"][CONF_CUSTOMER_ID], "100027")

    async def test_unique_id_is_set_from_customer_and_environment(self):
        """The unique id combines environment and customer id."""
        flow = self._flow()
        with patch(
            "custom_components.blaulichtsms_alarm.config_flow.validate_credentials",
            AsyncMock(return_value={}),
        ):
            await flow.async_step_user({**_CREDENTIALS, CONF_USE_STAGING: True})
        flow.async_set_unique_id.assert_awaited_once_with("staging-100027")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest custom_components.blaulichtsms_alarm.test_config_flow -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'custom_components.blaulichtsms_alarm.config_flow'`

- [ ] **Step 3: Write minimal implementation**

`custom_components/blaulichtsms_alarm/config_flow.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest custom_components.blaulichtsms_alarm.test_config_flow -v`
Expected: PASS, 10 Tests

- [ ] **Step 5: Lint und Commit**

```bash
uv run python -m ruff check
git add custom_components/blaulichtsms_alarm/config_flow.py custom_components/blaulichtsms_alarm/test_config_flow.py
git commit -m "feat: Einrichtungs-Wizard mit Zugangsdaten- und Gruppen-Schritt"
```

---

### Task 8: Services

Der größte Baustein. Handler sind Modulfunktionen, damit sie ohne laufendes Home Assistant testbar sind.

**Files:**
- Create: `custom_components/blaulichtsms_alarm/services.py`
- Test: `custom_components/blaulichtsms_alarm/test_services.py`

- [ ] **Step 1: Write the failing test**

`custom_components/blaulichtsms_alarm/test_services.py`:

```python
"""Unit tests for the blaulichtSMS Alarm services."""

import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp

from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .const import (
    ATTR_ADDITIONAL_MSISDNS,
    ATTR_ALARM_TEXT,
    ATTR_CONFIG_ENTRY,
    ATTR_GROUP_CODES,
    ATTR_NEEDS_ACKNOWLEDGEMENT,
    ATTR_START_DATE,
    TYPE_ALARM,
    TYPE_INFO,
)
from .errors import BlaulichtSmsApiError, BlaulichtSmsAuthError
from .services import async_list_alarms, async_query_alarm, async_trigger, resolve_entry


def _entry(entry_id="entry-1", group_filter=None, trigger_result=None, side_effect=None):
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
        with patch(
            "custom_components.blaulichtsms_alarm.services.async_dispatcher_send"
        ) as dispatch:
            result = await async_trigger(
                _hass(entry), call, alarm_type, with_start_date=with_start_date
            )
        return result, dispatch

    async def test_alarm_sends_type_alarm(self):
        """trigger_alarm sends type alarm and no start date."""
        entry = _entry()
        await self._trigger(
            entry, _call(**{ATTR_ALARM_TEXT: "Brand B2", ATTR_NEEDS_ACKNOWLEDGEMENT: True})
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
        _, dispatch = await self._trigger(
            entry, _call(**{ATTR_ALARM_TEXT: "Brand B2"})
        )
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
        await async_list_alarms(
            _hass(entry), _call(start_date=start, end_date=end)
        )
        entry.runtime_data.client.list_alarms.assert_awaited_once_with(
            start_date=start, end_date=end
        )

    async def test_query_uses_the_selected_entry(self):
        """The config_entry field selects the account to query."""
        first, second = _entry("a"), _entry("b")
        await async_query_alarm(
            _hass(first, second), _call(alarm_id="abc", **{ATTR_CONFIG_ENTRY: "b"})
        )
        second.runtime_data.client.query.assert_awaited_once()
        first.runtime_data.client.query.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest custom_components.blaulichtsms_alarm.test_services -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'custom_components.blaulichtsms_alarm.services'`

- [ ] **Step 3: Write minimal implementation**

`custom_components/blaulichtsms_alarm/services.py`:

```python
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
from .group_filter import (
    GroupNotAllowedError,
    GroupsRequiredError,
    resolve_group_codes,
)

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
```


- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest custom_components.blaulichtsms_alarm.test_services -v`
Expected: PASS, 24 Tests

- [ ] **Step 5: Lint und Commit**

```bash
uv run python -m ruff check
git add custom_components/blaulichtsms_alarm/services.py custom_components/blaulichtsms_alarm/test_services.py
git commit -m "feat: Services zum Auslösen und Abfragen von Alarmen"
```

---

### Task 9: services.yaml — Felddefinitionen für die HA-Oberfläche

`services.yaml` beschreibt nur die Struktur und die Selectors; die Texte kommen in Task 12 aus `strings.json`.

**Files:**
- Create: `custom_components/blaulichtsms_alarm/services.yaml`

- [ ] **Step 1: `services.yaml` schreiben**

```yaml
trigger_alarm: &trigger_fields
  fields:
    config_entry:
      required: false
      selector:
        config_entry:
          integration: blaulichtsms_alarm
    alarm_text:
      required: false
      example: "Brand B2, Hauptstraße 1"
      selector:
        text:
          multiline: true
    group_codes:
      required: false
      example: "['G1', 'G2']"
      selector:
        text:
          multiple: true
    needs_acknowledgement:
      required: false
      default: true
      selector:
        boolean:
    duration:
      required: false
      example: 60
      selector:
        number:
          min: 1
          max: 1440
          mode: box
    template:
      required: false
      example: "A1"
      selector:
        text:
    index_number:
      required: false
      example: 1
      selector:
        number:
          min: 0
          max: 999999
          mode: box
    additional_msisdns:
      required: false
      advanced: true
      example: "['+4366412345678']"
      selector:
        text:
          multiple: true
    hide_trigger_details:
      required: false
      advanced: true
      selector:
        boolean:
    recipient_confirmation:
      required: false
      advanced: true
      selector:
        boolean:
    recipient_confirmation_target:
      required: false
      advanced: true
      example: "+4366412345678"
      selector:
        text:
    location:
      required: false
      selector:
        location:
    address:
      required: false
      example: "Getreidemarkt 11, 1060 Wien"
      selector:
        text:

send_info: *trigger_fields

create_appointment:
  fields:
    config_entry:
      required: false
      selector:
        config_entry:
          integration: blaulichtsms_alarm
    start_date:
      required: true
      example: "2026-10-01 18:00:00"
      selector:
        datetime:
    alarm_text:
      required: false
      example: "Monatsschulung im Rüsthaus"
      selector:
        text:
          multiline: true
    group_codes:
      required: false
      example: "['G1']"
      selector:
        text:
          multiple: true
    needs_acknowledgement:
      required: false
      default: true
      selector:
        boolean:
    duration:
      required: false
      example: 60
      selector:
        number:
          min: 1
          max: 1440
          mode: box
    template:
      required: false
      selector:
        text:
    index_number:
      required: false
      selector:
        number:
          min: 0
          max: 999999
          mode: box
    additional_msisdns:
      required: false
      advanced: true
      selector:
        text:
          multiple: true
    hide_trigger_details:
      required: false
      advanced: true
      selector:
        boolean:
    recipient_confirmation:
      required: false
      advanced: true
      selector:
        boolean:
    recipient_confirmation_target:
      required: false
      advanced: true
      selector:
        text:
    location:
      required: false
      selector:
        location:
    address:
      required: false
      selector:
        text:

query_alarm:
  fields:
    config_entry:
      required: false
      selector:
        config_entry:
          integration: blaulichtsms_alarm
    alarm_id:
      required: true
      example: "dakldjsfal-2343232-afsdaddfa-234"
      selector:
        text:

list_alarms:
  fields:
    config_entry:
      required: false
      selector:
        config_entry:
          integration: blaulichtsms_alarm
    start_date:
      required: false
      selector:
        datetime:
    end_date:
      required: false
      selector:
        datetime:
```

- [ ] **Step 2: YAML validieren**

Run: `yq . custom_components/blaulichtsms_alarm/services.yaml > /dev/null && echo OK`
Expected: `OK`

- [ ] **Step 3: Prüfen, dass jedes Feld auch im Schema existiert**

Run:
```bash
uv run python - <<'PY'
import yaml
from custom_components.blaulichtsms_alarm import services

schemas = {
    "trigger_alarm": services.TRIGGER_SCHEMA,
    "send_info": services.TRIGGER_SCHEMA,
    "create_appointment": services.APPOINTMENT_SCHEMA,
    "query_alarm": services.QUERY_SCHEMA,
    "list_alarms": services.LIST_SCHEMA,
}
with open("custom_components/blaulichtsms_alarm/services.yaml") as handle:
    doc = yaml.safe_load(handle)
for name, schema in schemas.items():
    known = {str(key) for key in schema.schema}
    declared = set(doc[name]["fields"])
    assert declared <= known, f"{name}: unbekannte Felder {declared - known}"
    print(name, "ok", len(declared), "Felder")
PY
```
Expected: fünf `ok`-Zeilen, kein AssertionError

- [ ] **Step 4: Commit**

```bash
git add custom_components/blaulichtsms_alarm/services.yaml
git commit -m "feat: Felddefinitionen für die Service-Oberfläche"
```

---

### Task 10: Setup des Config Entry

**Files:**
- Modify: `custom_components/blaulichtsms_alarm/__init__.py`
- Test: `custom_components/blaulichtsms_alarm/test_init.py`

- [ ] **Step 1: Write the failing test**

`custom_components/blaulichtsms_alarm/test_init.py`:

```python
"""Unit tests for the integration setup."""

import unittest
from types import SimpleNamespace
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
            patch(
                "custom_components.blaulichtsms_alarm.AlarmApiClient",
                return_value=client,
            ) as factory,
            patch("custom_components.blaulichtsms_alarm.async_get_clientsession"),
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
        _, factory, _ = await self._setup(
            self._entry(**{CONF_USE_STAGING: True})
        )
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest custom_components.blaulichtsms_alarm.test_init -v`
Expected: FAIL — `ImportError: cannot import name 'async_setup_entry'`

- [ ] **Step 3: Write minimal implementation**

`custom_components/blaulichtsms_alarm/__init__.py` (ersetzt die leere Datei):

```python
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
```


- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest custom_components.blaulichtsms_alarm.test_init -v`
Expected: PASS, 8 Tests

- [ ] **Step 5: Lint und Commit**

```bash
uv run python -m ruff check
git add custom_components/blaulichtsms_alarm/__init__.py custom_components/blaulichtsms_alarm/test_init.py
git commit -m "feat: Setup des Config Entry mit Zugangsdaten-Prüfung"
```

---

### Task 11: Sensor "letzter ausgelöster Alarm"

**Files:**
- Create: `custom_components/blaulichtsms_alarm/sensor.py`
- Test: `custom_components/blaulichtsms_alarm/test_sensor.py`

- [ ] **Step 1: Write the failing test**

`custom_components/blaulichtsms_alarm/test_sensor.py`:

```python
"""Unit tests for the last triggered alarm sensor."""

import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from .const import TYPE_ALARM
from .sensor import BlaulichtSmsLastTriggeredSensor, parse_restored_state

_TRIGGERED_AT = datetime(2026, 9, 6, 12, 0, tzinfo=UTC)
_LAST_ALARM = {
    "alarm_id": "abc",
    "alarm_text": "Brand B2",
    "type": TYPE_ALARM,
    "group_codes": ["G1"],
    "result": "OK",
    "triggered_at": _TRIGGERED_AT,
}


class TestParseRestoredState(unittest.TestCase):
    """Tests for parse_restored_state."""

    def test_none_state(self):
        """Without a restored state there is nothing to show."""
        self.assertEqual(parse_restored_state(None), (None, {}))

    def test_unknown_state(self):
        """An unknown state restores nothing."""
        state = SimpleNamespace(state="unknown", attributes={})
        self.assertEqual(parse_restored_state(state), (None, {}))

    def test_timestamp_and_attributes_are_restored(self):
        """A stored timestamp and the known attributes come back."""
        state = SimpleNamespace(
            state="2026-09-06T12:00:00+00:00",
            attributes={
                "alarm_id": "abc",
                "alarm_text": "Brand B2",
                "type": TYPE_ALARM,
                "group_codes": ["G1"],
                "result": "OK",
                "device_class": "timestamp",
            },
        )
        value, attributes = parse_restored_state(state)
        self.assertEqual(value, _TRIGGERED_AT)
        self.assertEqual(attributes["alarm_id"], "abc")
        self.assertNotIn("device_class", attributes)


class TestSensor(unittest.TestCase):
    """Tests for BlaulichtSmsLastTriggeredSensor."""

    def _sensor(self, last_alarm=None):
        """Build a sensor without running the entity machinery."""
        sensor = BlaulichtSmsLastTriggeredSensor.__new__(
            BlaulichtSmsLastTriggeredSensor
        )
        sensor._entry = SimpleNamespace(
            entry_id="entry-1",
            runtime_data=SimpleNamespace(last_alarm=last_alarm),
        )
        sensor._value = None
        sensor._attributes = {}
        sensor.async_write_ha_state = MagicMock()
        return sensor

    def test_value_is_none_before_the_first_alarm(self):
        """Without an alarm the sensor has no value."""
        sensor = self._sensor()
        self.assertIsNone(sensor.native_value)
        self.assertEqual(sensor.extra_state_attributes, {})

    def test_trigger_sets_value_and_attributes(self):
        """A dispatched trigger copies the last alarm into the state."""
        sensor = self._sensor(_LAST_ALARM)
        sensor._handle_trigger()
        self.assertEqual(sensor.native_value, _TRIGGERED_AT)
        self.assertEqual(sensor.extra_state_attributes["alarm_id"], "abc")
        self.assertEqual(sensor.extra_state_attributes["alarm_text"], "Brand B2")
        self.assertEqual(sensor.extra_state_attributes["group_codes"], ["G1"])
        sensor.async_write_ha_state.assert_called_once()

    def test_trigger_without_data_keeps_the_previous_state(self):
        """A trigger without runtime data does not clear the state."""
        sensor = self._sensor()
        sensor._value = _TRIGGERED_AT
        sensor._apply_last_alarm(None)
        self.assertEqual(sensor.native_value, _TRIGGERED_AT)

    def test_attributes_do_not_leak_triggered_at(self):
        """The timestamp is the state, not an attribute."""
        sensor = self._sensor(_LAST_ALARM)
        sensor._apply_last_alarm(_LAST_ALARM)
        self.assertNotIn("triggered_at", sensor.extra_state_attributes)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest custom_components.blaulichtsms_alarm.test_sensor -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'custom_components.blaulichtsms_alarm.sensor'`

- [ ] **Step 3: Write minimal implementation**

`custom_components/blaulichtsms_alarm/sensor.py`:

```python
"""Sensor showing the last alarm triggered through this integration."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, SIGNAL_ALARM_TRIGGERED, VERSION

RESTORED_ATTRIBUTES = ("alarm_id", "alarm_text", "type", "group_codes", "result")


def parse_restored_state(state: Any) -> tuple[datetime | None, dict[str, Any]]:
    """Turn a restored Home Assistant state into a value and attributes."""
    if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE, None):
        return None, {}
    return (
        dt_util.parse_datetime(state.state),
        {
            key: state.attributes[key]
            for key in RESTORED_ATTRIBUTES
            if key in state.attributes
        },
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensor of a config entry."""
    async_add_entities([BlaulichtSmsLastTriggeredSensor(entry)])


class BlaulichtSmsLastTriggeredSensor(SensorEntity, RestoreEntity):
    """Timestamp of the last alarm triggered through this integration."""

    _attr_has_entity_name = True
    _attr_translation_key = "last_triggered"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_should_poll = False

    def __init__(self, entry: Any) -> None:
        """Bind the sensor to a config entry."""
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_last_triggered"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="blaulichtSMS",
            model="Alarm API v1",
            sw_version=VERSION,
        )
        self._value: datetime | None = None
        self._attributes: dict[str, Any] = {}

    @property
    def native_value(self) -> datetime | None:
        """Return the time of the last triggered alarm."""
        return self._value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return details of the last triggered alarm."""
        return self._attributes

    async def async_added_to_hass(self) -> None:
        """Restore the previous state and subscribe to trigger events."""
        await super().async_added_to_hass()

        self._apply_last_alarm(self._entry.runtime_data.last_alarm)
        if self._value is None:
            self._value, self._attributes = parse_restored_state(
                await self.async_get_last_state()
            )

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_ALARM_TRIGGERED}_{self._entry.entry_id}",
                self._handle_trigger,
            )
        )

    @callback
    def _handle_trigger(self) -> None:
        """Take over the alarm a service just triggered."""
        self._apply_last_alarm(self._entry.runtime_data.last_alarm)
        self.async_write_ha_state()

    def _apply_last_alarm(self, last_alarm: dict[str, Any] | None) -> None:
        """Copy a triggered alarm into the entity state."""
        if not last_alarm:
            return
        self._value = last_alarm.get("triggered_at")
        self._attributes = {key: last_alarm.get(key) for key in RESTORED_ATTRIBUTES}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest custom_components.blaulichtsms_alarm.test_sensor -v`
Expected: PASS, 7 Tests

- [ ] **Step 5: Lint und Commit**

```bash
uv run python -m ruff check
git add custom_components/blaulichtsms_alarm/sensor.py custom_components/blaulichtsms_alarm/test_sensor.py
git commit -m "feat: Sensor für den zuletzt ausgelösten Alarm"
```

---

### Task 12: Texte und Übersetzungen

**Files:**
- Create: `custom_components/blaulichtsms_alarm/strings.json`
- Create: `custom_components/blaulichtsms_alarm/translations/en.json`
- Create: `custom_components/blaulichtsms_alarm/translations/de.json`

- [ ] **Step 1: `strings.json` schreiben**

```json
{
  "title": "blaulichtSMS Alarm",
  "config": {
    "step": {
      "user": {
        "title": "blaulichtSMS Alarm API",
        "description": "Enter the credentials of the automatic alarm trigger configured for your customer id. The credentials are verified with a read-only request; no alarm is triggered.",
        "data": {
          "customer_id": "Customer ID",
          "username": "Username",
          "password": "Password",
          "use_staging": "Use the test API (api-staging.blaulichtsms.net)"
        }
      },
      "groups": {
        "title": "Alarm group filter",
        "description": "Optional: comma separated list of alarm group codes that may be alerted, for example G1,G2. If a filter is set, every service call must name its groups explicitly and only these groups are accepted. Leave empty to allow all groups.",
        "data": {
          "group_filter": "Allowed alarm groups"
        }
      },
      "reauth_confirm": {
        "title": "Re-authenticate blaulichtSMS Alarm",
        "description": "Your credentials are no longer valid. Please enter them again.",
        "data": {
          "username": "Username",
          "password": "Password"
        }
      },
      "reconfigure": {
        "title": "Change blaulichtSMS Alarm credentials",
        "description": "Update the username and password of the automatic alarm trigger.",
        "data": {
          "username": "Username",
          "password": "Password"
        }
      }
    },
    "error": {
      "invalid_auth": "Authentication failed. Check customer ID, username and password.",
      "cannot_connect": "Could not reach the blaulichtSMS alarm API",
      "unknown": "The blaulichtSMS alarm API returned an unexpected error"
    },
    "abort": {
      "already_configured": "This customer is already configured",
      "reauth_successful": "Re-authentication successful",
      "reconfigure_successful": "Credentials updated successfully"
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "Alarm group filter",
        "description": "Comma separated list of alarm group codes that may be alerted. Leave empty to allow all groups.",
        "data": {
          "group_filter": "Allowed alarm groups"
        }
      }
    }
  },
  "entity": {
    "sensor": {
      "last_triggered": { "name": "Last triggered alarm" }
    }
  },
  "exceptions": {
    "no_entry": {
      "message": "No blaulichtSMS Alarm account is configured."
    },
    "entry_required": {
      "message": "Several blaulichtSMS Alarm accounts are configured. Choose one with the config_entry field."
    },
    "entry_not_found": {
      "message": "No loaded blaulichtSMS Alarm account with the id {entry_id}."
    },
    "groups_required": {
      "message": "An alarm group filter is configured, so group_codes must be given. Allowed groups: {allowed}."
    },
    "group_not_allowed": {
      "message": "The alarm groups {groups} are not allowed. Allowed groups: {allowed}."
    },
    "msisdns_not_allowed": {
      "message": "additional_msisdns cannot be used while an alarm group filter is configured, because single numbers would bypass the filter."
    }
  },
  "services": {
    "trigger_alarm": {
      "name": "Trigger alarm",
      "description": "Triggers a blaulichtSMS alarm immediately.",
      "fields": {
        "config_entry": {
          "name": "Account",
          "description": "The blaulichtSMS account to use. Can be omitted if only one is configured."
        },
        "alarm_text": { "name": "Alarm text", "description": "Text of the alarm." },
        "group_codes": {
          "name": "Alarm groups",
          "description": "Group codes to alert, for example G1. Required if a group filter is configured."
        },
        "needs_acknowledgement": {
          "name": "Reply function",
          "description": "Ask recipients to confirm whether they are coming."
        },
        "duration": {
          "name": "Reply window",
          "description": "How long the reply function stays open. According to the blaulichtSMS documentation the value is in minutes."
        },
        "template": {
          "name": "Alarm text code",
          "description": "Code of a predefined alarm text, for example A1."
        },
        "index_number": {
          "name": "Index number",
          "description": "Reusing an index number updates the text of that alarm instead of creating a new one."
        },
        "additional_msisdns": {
          "name": "Additional numbers",
          "description": "Extra phone numbers to alert. Blocked while an alarm group filter is configured."
        },
        "hide_trigger_details": {
          "name": "Hide trigger details",
          "description": "Do not send details about who triggered the alarm."
        },
        "recipient_confirmation": {
          "name": "Delivery confirmation",
          "description": "Confirm that the SMS was received. Additional charges apply."
        },
        "recipient_confirmation_target": {
          "name": "Confirmation recipient",
          "description": "Phone number that receives the delivery confirmation."
        },
        "location": {
          "name": "Location",
          "description": "Coordinates of the incident. Takes precedence over the address."
        },
        "address": {
          "name": "Address",
          "description": "Address of the incident; blaulichtSMS converts it to coordinates."
        }
      }
    },
    "send_info": {
      "name": "Send info",
      "description": "Sends a blaulichtSMS info message immediately.",
      "fields": {
        "config_entry": {
          "name": "Account",
          "description": "The blaulichtSMS account to use. Can be omitted if only one is configured."
        },
        "alarm_text": { "name": "Info text", "description": "Text of the info." },
        "group_codes": {
          "name": "Alarm groups",
          "description": "Group codes to notify, for example G1. Required if a group filter is configured."
        },
        "needs_acknowledgement": {
          "name": "Reply function",
          "description": "Ask recipients to reply."
        },
        "duration": {
          "name": "Reply window",
          "description": "How long the reply function stays open. According to the blaulichtSMS documentation the value is in minutes."
        },
        "template": {
          "name": "Text code",
          "description": "Code of a predefined text, for example A1."
        },
        "index_number": {
          "name": "Index number",
          "description": "Reusing an index number updates the text of that message."
        },
        "additional_msisdns": {
          "name": "Additional numbers",
          "description": "Extra phone numbers to notify. Blocked while an alarm group filter is configured."
        },
        "hide_trigger_details": {
          "name": "Hide trigger details",
          "description": "Do not send details about who sent the info."
        },
        "recipient_confirmation": {
          "name": "Delivery confirmation",
          "description": "Confirm that the SMS was received. Additional charges apply."
        },
        "recipient_confirmation_target": {
          "name": "Confirmation recipient",
          "description": "Phone number that receives the delivery confirmation."
        },
        "location": {
          "name": "Location",
          "description": "Coordinates to attach. Takes precedence over the address."
        },
        "address": {
          "name": "Address",
          "description": "Address to attach; blaulichtSMS converts it to coordinates."
        }
      }
    },
    "create_appointment": {
      "name": "Create appointment",
      "description": "Creates a blaulichtSMS appointment: an info message delivered at a future point in time.",
      "fields": {
        "config_entry": {
          "name": "Account",
          "description": "The blaulichtSMS account to use. Can be omitted if only one is configured."
        },
        "start_date": {
          "name": "Date and time",
          "description": "When the appointment message is sent."
        },
        "alarm_text": {
          "name": "Appointment text",
          "description": "Text of the appointment."
        },
        "group_codes": {
          "name": "Alarm groups",
          "description": "Group codes to invite, for example G1. Required if a group filter is configured."
        },
        "needs_acknowledgement": {
          "name": "Reply function",
          "description": "Ask recipients to confirm whether they are attending."
        },
        "duration": {
          "name": "Reply window",
          "description": "How long the reply function stays open. According to the blaulichtSMS documentation the value is in minutes."
        },
        "template": {
          "name": "Text code",
          "description": "Code of a predefined text, for example A1."
        },
        "index_number": {
          "name": "Index number",
          "description": "Reusing an index number updates that appointment."
        },
        "additional_msisdns": {
          "name": "Additional numbers",
          "description": "Extra phone numbers to invite. Blocked while an alarm group filter is configured."
        },
        "hide_trigger_details": {
          "name": "Hide trigger details",
          "description": "Do not send details about who created the appointment."
        },
        "recipient_confirmation": {
          "name": "Delivery confirmation",
          "description": "Confirm that the SMS was received. Additional charges apply."
        },
        "recipient_confirmation_target": {
          "name": "Confirmation recipient",
          "description": "Phone number that receives the delivery confirmation."
        },
        "location": {
          "name": "Location",
          "description": "Coordinates of the appointment. Takes precedence over the address."
        },
        "address": {
          "name": "Address",
          "description": "Address of the appointment; blaulichtSMS converts it to coordinates."
        }
      }
    },
    "query_alarm": {
      "name": "Query alarm",
      "description": "Returns the current data of a single alarm, including the replies.",
      "fields": {
        "config_entry": {
          "name": "Account",
          "description": "The blaulichtSMS account to use. Can be omitted if only one is configured."
        },
        "alarm_id": {
          "name": "Alarm ID",
          "description": "The id returned when the alarm was triggered."
        }
      }
    },
    "list_alarms": {
      "name": "List alarms",
      "description": "Returns up to 100 alarms of the configured customer.",
      "fields": {
        "config_entry": {
          "name": "Account",
          "description": "The blaulichtSMS account to use. Can be omitted if only one is configured."
        },
        "start_date": {
          "name": "From",
          "description": "Only alarms that ended after this point in time."
        },
        "end_date": {
          "name": "Until",
          "description": "Only alarms that started before this point in time."
        }
      }
    }
  }
}
```

- [ ] **Step 2: `translations/en.json` als Kopie anlegen**

```bash
cp custom_components/blaulichtsms_alarm/strings.json custom_components/blaulichtsms_alarm/translations/en.json
```

- [ ] **Step 3: `translations/de.json` schreiben**

```json
{
  "title": "blaulichtSMS Alarm",
  "config": {
    "step": {
      "user": {
        "title": "blaulichtSMS Alarm API",
        "description": "Zugangsdaten des für deine Kundennummer eingerichteten automatischen Alarmauslösers eintragen. Die Prüfung erfolgt über eine reine Leseabfrage; es wird kein Alarm ausgelöst.",
        "data": {
          "customer_id": "Kundennummer",
          "username": "Benutzername",
          "password": "Passwort",
          "use_staging": "Test-API verwenden (api-staging.blaulichtsms.net)"
        }
      },
      "groups": {
        "title": "Alarmgruppen-Filter",
        "description": "Optional: kommagetrennte Liste der Gruppencodes, die alarmiert werden dürfen, z. B. G1,G2. Ist ein Filter gesetzt, muss jeder Service-Aufruf seine Gruppen ausdrücklich nennen und es werden nur diese Gruppen akzeptiert. Leer lassen, um alle Gruppen zu erlauben.",
        "data": {
          "group_filter": "Erlaubte Alarmgruppen"
        }
      },
      "reauth_confirm": {
        "title": "blaulichtSMS Alarm erneut authentifizieren",
        "description": "Die Zugangsdaten sind nicht mehr gültig. Bitte erneut eingeben.",
        "data": {
          "username": "Benutzername",
          "password": "Passwort"
        }
      },
      "reconfigure": {
        "title": "blaulichtSMS Alarm Zugangsdaten ändern",
        "description": "Benutzername und Passwort des automatischen Alarmauslösers aktualisieren.",
        "data": {
          "username": "Benutzername",
          "password": "Passwort"
        }
      }
    },
    "error": {
      "invalid_auth": "Authentifizierung fehlgeschlagen. Kundennummer, Benutzername und Passwort prüfen.",
      "cannot_connect": "Die blaulichtSMS Alarm API ist nicht erreichbar",
      "unknown": "Die blaulichtSMS Alarm API hat einen unerwarteten Fehler gemeldet"
    },
    "abort": {
      "already_configured": "Diese Kundennummer ist bereits konfiguriert",
      "reauth_successful": "Erneute Authentifizierung erfolgreich",
      "reconfigure_successful": "Zugangsdaten erfolgreich aktualisiert"
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "Alarmgruppen-Filter",
        "description": "Kommagetrennte Liste der Gruppencodes, die alarmiert werden dürfen. Leer lassen, um alle Gruppen zu erlauben.",
        "data": {
          "group_filter": "Erlaubte Alarmgruppen"
        }
      }
    }
  },
  "entity": {
    "sensor": {
      "last_triggered": { "name": "Zuletzt ausgelöster Alarm" }
    }
  },
  "exceptions": {
    "no_entry": {
      "message": "Es ist kein blaulichtSMS Alarm Konto konfiguriert."
    },
    "entry_required": {
      "message": "Es sind mehrere blaulichtSMS Alarm Konten konfiguriert. Wähle eines über das Feld config_entry aus."
    },
    "entry_not_found": {
      "message": "Kein geladenes blaulichtSMS Alarm Konto mit der ID {entry_id}."
    },
    "groups_required": {
      "message": "Es ist ein Alarmgruppen-Filter konfiguriert, daher müssen group_codes angegeben werden. Erlaubte Gruppen: {allowed}."
    },
    "group_not_allowed": {
      "message": "Die Alarmgruppen {groups} sind nicht erlaubt. Erlaubte Gruppen: {allowed}."
    },
    "msisdns_not_allowed": {
      "message": "additional_msisdns kann nicht verwendet werden, solange ein Alarmgruppen-Filter konfiguriert ist, weil einzelne Rufnummern den Filter umgehen würden."
    }
  },
  "services": {
    "trigger_alarm": {
      "name": "Alarm auslösen",
      "description": "Löst sofort einen blaulichtSMS Alarm aus.",
      "fields": {
        "config_entry": {
          "name": "Konto",
          "description": "Das zu verwendende blaulichtSMS Konto. Kann entfallen, wenn nur eines konfiguriert ist."
        },
        "alarm_text": { "name": "Alarmtext", "description": "Text des Alarms." },
        "group_codes": {
          "name": "Alarmgruppen",
          "description": "Zu alarmierende Gruppencodes, z. B. G1. Pflicht, wenn ein Gruppen-Filter konfiguriert ist."
        },
        "needs_acknowledgement": {
          "name": "Rückmeldefunktion",
          "description": "Empfänger um Rückmeldung bitten, ob sie kommen."
        },
        "duration": {
          "name": "Rückmeldefenster",
          "description": "Wie lange die Rückmeldefunktion offen bleibt. Laut blaulichtSMS Dokumentation in Minuten."
        },
        "template": {
          "name": "Alarmtext-Code",
          "description": "Code eines hinterlegten Alarmtextes, z. B. A1."
        },
        "index_number": {
          "name": "Indexnummer",
          "description": "Eine erneut verwendete Indexnummer aktualisiert den Text dieses Alarms, statt einen neuen auszulösen."
        },
        "additional_msisdns": {
          "name": "Zusätzliche Rufnummern",
          "description": "Weitere zu alarmierende Rufnummern. Gesperrt, solange ein Alarmgruppen-Filter konfiguriert ist."
        },
        "hide_trigger_details": {
          "name": "Auslöser verbergen",
          "description": "Keine Details darüber senden, wer den Alarm ausgelöst hat."
        },
        "recipient_confirmation": {
          "name": "Zustellbestätigung",
          "description": "Bestätigen, dass die SMS empfangen wurde. Kostenpflichtig."
        },
        "recipient_confirmation_target": {
          "name": "Empfänger der Bestätigung",
          "description": "Rufnummer, die die Zustellbestätigung erhält."
        },
        "location": {
          "name": "Einsatzort",
          "description": "Koordinaten des Einsatzortes. Haben Vorrang vor der Adresse."
        },
        "address": {
          "name": "Adresse",
          "description": "Adresse des Einsatzortes; blaulichtSMS wandelt sie in Koordinaten um."
        }
      }
    },
    "send_info": {
      "name": "Info senden",
      "description": "Sendet sofort eine blaulichtSMS Info.",
      "fields": {
        "config_entry": {
          "name": "Konto",
          "description": "Das zu verwendende blaulichtSMS Konto. Kann entfallen, wenn nur eines konfiguriert ist."
        },
        "alarm_text": { "name": "Infotext", "description": "Text der Info." },
        "group_codes": {
          "name": "Alarmgruppen",
          "description": "Zu verständigende Gruppencodes, z. B. G1. Pflicht, wenn ein Gruppen-Filter konfiguriert ist."
        },
        "needs_acknowledgement": {
          "name": "Rückmeldefunktion",
          "description": "Empfänger um eine Rückmeldung bitten."
        },
        "duration": {
          "name": "Rückmeldefenster",
          "description": "Wie lange die Rückmeldefunktion offen bleibt. Laut blaulichtSMS Dokumentation in Minuten."
        },
        "template": {
          "name": "Text-Code",
          "description": "Code eines hinterlegten Textes, z. B. A1."
        },
        "index_number": {
          "name": "Indexnummer",
          "description": "Eine erneut verwendete Indexnummer aktualisiert den Text dieser Nachricht."
        },
        "additional_msisdns": {
          "name": "Zusätzliche Rufnummern",
          "description": "Weitere zu verständigende Rufnummern. Gesperrt, solange ein Alarmgruppen-Filter konfiguriert ist."
        },
        "hide_trigger_details": {
          "name": "Auslöser verbergen",
          "description": "Keine Details darüber senden, wer die Info gesendet hat."
        },
        "recipient_confirmation": {
          "name": "Zustellbestätigung",
          "description": "Bestätigen, dass die SMS empfangen wurde. Kostenpflichtig."
        },
        "recipient_confirmation_target": {
          "name": "Empfänger der Bestätigung",
          "description": "Rufnummer, die die Zustellbestätigung erhält."
        },
        "location": {
          "name": "Ort",
          "description": "Anzuhängende Koordinaten. Haben Vorrang vor der Adresse."
        },
        "address": {
          "name": "Adresse",
          "description": "Anzuhängende Adresse; blaulichtSMS wandelt sie in Koordinaten um."
        }
      }
    },
    "create_appointment": {
      "name": "Termin erstellen",
      "description": "Erstellt einen blaulichtSMS Termin: eine Info, die zu einem zukünftigen Zeitpunkt zugestellt wird.",
      "fields": {
        "config_entry": {
          "name": "Konto",
          "description": "Das zu verwendende blaulichtSMS Konto. Kann entfallen, wenn nur eines konfiguriert ist."
        },
        "start_date": {
          "name": "Datum und Uhrzeit",
          "description": "Wann die Terminnachricht gesendet wird."
        },
        "alarm_text": {
          "name": "Termintext",
          "description": "Text des Termins."
        },
        "group_codes": {
          "name": "Alarmgruppen",
          "description": "Einzuladende Gruppencodes, z. B. G1. Pflicht, wenn ein Gruppen-Filter konfiguriert ist."
        },
        "needs_acknowledgement": {
          "name": "Rückmeldefunktion",
          "description": "Empfänger um Rückmeldung bitten, ob sie teilnehmen."
        },
        "duration": {
          "name": "Rückmeldefenster",
          "description": "Wie lange die Rückmeldefunktion offen bleibt. Laut blaulichtSMS Dokumentation in Minuten."
        },
        "template": {
          "name": "Text-Code",
          "description": "Code eines hinterlegten Textes, z. B. A1."
        },
        "index_number": {
          "name": "Indexnummer",
          "description": "Eine erneut verwendete Indexnummer aktualisiert diesen Termin."
        },
        "additional_msisdns": {
          "name": "Zusätzliche Rufnummern",
          "description": "Weitere einzuladende Rufnummern. Gesperrt, solange ein Alarmgruppen-Filter konfiguriert ist."
        },
        "hide_trigger_details": {
          "name": "Auslöser verbergen",
          "description": "Keine Details darüber senden, wer den Termin erstellt hat."
        },
        "recipient_confirmation": {
          "name": "Zustellbestätigung",
          "description": "Bestätigen, dass die SMS empfangen wurde. Kostenpflichtig."
        },
        "recipient_confirmation_target": {
          "name": "Empfänger der Bestätigung",
          "description": "Rufnummer, die die Zustellbestätigung erhält."
        },
        "location": {
          "name": "Ort",
          "description": "Koordinaten des Termins. Haben Vorrang vor der Adresse."
        },
        "address": {
          "name": "Adresse",
          "description": "Adresse des Termins; blaulichtSMS wandelt sie in Koordinaten um."
        }
      }
    },
    "query_alarm": {
      "name": "Alarm abfragen",
      "description": "Liefert die aktuellen Daten eines einzelnen Alarms samt Rückmeldungen.",
      "fields": {
        "config_entry": {
          "name": "Konto",
          "description": "Das zu verwendende blaulichtSMS Konto. Kann entfallen, wenn nur eines konfiguriert ist."
        },
        "alarm_id": {
          "name": "Alarm-ID",
          "description": "Die ID, die beim Auslösen des Alarms zurückgegeben wurde."
        }
      }
    },
    "list_alarms": {
      "name": "Alarme auflisten",
      "description": "Liefert bis zu 100 Alarme der konfigurierten Kundennummer.",
      "fields": {
        "config_entry": {
          "name": "Konto",
          "description": "Das zu verwendende blaulichtSMS Konto. Kann entfallen, wenn nur eines konfiguriert ist."
        },
        "start_date": {
          "name": "Von",
          "description": "Nur Alarme, die nach diesem Zeitpunkt geendet haben."
        },
        "end_date": {
          "name": "Bis",
          "description": "Nur Alarme, die vor diesem Zeitpunkt begonnen haben."
        }
      }
    }
  }
}
```

- [ ] **Step 4: Prüfen, dass alle Übersetzungen dieselben Schlüssel haben und alle verwendeten Schlüssel existieren**

Run:
```bash
uv run python - <<'PY'
import json
from pathlib import Path

base = Path("custom_components/blaulichtsms_alarm")


def keys(node, prefix=""):
    """Flatten a nested dict into dotted keys."""
    if not isinstance(node, dict):
        return {prefix}
    out = set()
    for key, value in node.items():
        out |= keys(value, f"{prefix}.{key}" if prefix else key)
    return out


strings = json.loads((base / "strings.json").read_text())
de = json.loads((base / "translations" / "de.json").read_text())
en = json.loads((base / "translations" / "en.json").read_text())

assert keys(strings) == keys(en), keys(strings) ^ keys(en)
assert keys(strings) == keys(de), keys(strings) ^ keys(de)

import yaml

doc = yaml.safe_load((base / "services.yaml").read_text())
for name, spec in doc.items():
    assert name in strings["services"], f"missing service text: {name}"
    for field in spec["fields"]:
        assert field in strings["services"][name]["fields"], f"{name}.{field}"

for key in (
    "no_entry",
    "entry_required",
    "entry_not_found",
    "groups_required",
    "group_not_allowed",
    "msisdns_not_allowed",
):
    assert key in strings["exceptions"], key

print("translations ok:", len(keys(strings)), "keys")
PY
```
Expected: `translations ok: <n> keys`, kein AssertionError

- [ ] **Step 5: Commit**

```bash
git add custom_components/blaulichtsms_alarm/strings.json custom_components/blaulichtsms_alarm/translations
git commit -m "feat: deutsche und englische Texte für Wizard, Services und Fehler"
```

---

### Task 13: CI und Release

**Files:**
- Create: `.github/workflows/pull_request.yml`
- Create: `.github/workflows/release-please.yml`
- Create: `.github/dependabot.yml`

- [ ] **Step 1: `.github/workflows/pull_request.yml` schreiben**

```yaml
name: "Pull Request"

on:
  pull_request:
    branches:
      - main

permissions: {}

jobs:
  pull_request:
    name: "Lint and Test"
    runs-on: "ubuntu-latest"
    steps:
      - name: "Checkout the repository"
        uses: "actions/checkout@v7.0.1"

      - name: "Set up Python"
        uses: actions/setup-python@v7.0.0
        with:
          python-version: "3.14"
          cache: "pip"

      - name: "Install requirements"
        run: |
          python3 -m pip install uv &&
          uv venv &&
          uv pip install -r requirements.txt

      - name: "Lint"
        run: uv run python -m ruff check

      - name: "Test"
        run: uv run python -m unittest discover -v
```

- [ ] **Step 2: `.github/workflows/release-please.yml` schreiben**

```yaml
name: "Release Please"

on:
  push:
    branches:
      - main

permissions: {}

jobs:
  release-please:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    steps:
      - uses: googleapis/release-please-action@v5
        id: release
        with:
          token: ${{ secrets.RELEASE_PLEASE_TOKEN }}
          config-file: release-please-config.json
          manifest-file: .release-please-manifest.json

      - uses: actions/checkout@v7.0.1
        if: ${{ steps.release.outputs.release_created }}

      - name: "ZIP the integration directory"
        if: ${{ steps.release.outputs.release_created }}
        shell: "bash"
        run: |
          cd "$GITHUB_WORKSPACE/custom_components/blaulichtsms_alarm"
          zip blaulichtsms_alarm.zip -r ./

      - name: "Upload the ZIP file to the release"
        if: ${{ steps.release.outputs.release_created }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          TAG_NAME: ${{ steps.release.outputs.tag_name }}
          REPO: ${{ github.repository }}
        run: |
          gh release upload "$TAG_NAME" \
            "$GITHUB_WORKSPACE/custom_components/blaulichtsms_alarm/blaulichtsms_alarm.zip" \
            --repo "$REPO"
```

- [ ] **Step 3: `.github/dependabot.yml` schreiben**

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    commit-message:
      prefix: "fix(deps)"
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    commit-message:
      prefix: "ci"
```

- [ ] **Step 4: YAML validieren und committen**

```bash
for f in .github/workflows/*.yml .github/dependabot.yml; do yq . "$f" > /dev/null && echo "OK $f"; done
git add .github
git commit -m "ci: Lint-, Test- und Release-Pipeline"
```

---

### Task 14: Dokumentation

**Files:**
- Modify: `README.md`
- Create: `CLAUDE.md`

- [ ] **Step 1: `README.md` schreiben**

```markdown
# blaulichtSMS Alarm für Home Assistant

Home-Assistant-Integration, mit der aus Automatisierungen heraus
[blaulichtSMS](https://blaulichtsms.net/) Alarme, Infos und Termine **ausgelöst**
werden können.

Sie ist das Gegenstück zu
[hassio_blaulichtsms](https://github.com/r00tat/hassio_blaulichtsms), das Alarme
nur abruft. Beide Integrationen können parallel installiert sein.

Grundlage ist die
[blaulichtSMS Alarm API v1](https://github.com/blaulichtSMS/docs/blob/master/alarm_api_v1.md).

## Voraussetzungen

Für die Kundennummer muss bei blaulichtSMS ein **automatischer Alarmauslöser**
mit Benutzername und Passwort eingerichtet sein. Das sind andere Zugangsdaten
als die des Einsatzmonitors.

## Installation

1. HACS öffnen, 3 Punkte, "Benutzerdefinierte Repositories"
2. `https://github.com/r00tat/homeassistant-blaulichtsms-alarm` als Repository,
   Kategorie `Integration`
3. "blaulichtSMS Alarm" installieren und Home Assistant neu starten
4. Integration hinzufügen und dem Wizard folgen

## Einrichtung

Der Wizard hat zwei Schritte:

1. **Zugangsdaten** — Kundennummer, Benutzername, Passwort. Optional kann die
   Test-API verwendet werden, um Automatisierungen gefahrlos zu erproben. Die
   Prüfung erfolgt über eine reine Leseabfrage, es wird kein Alarm ausgelöst.
2. **Alarmgruppen-Filter** — optionale, kommagetrennte Liste der Gruppencodes,
   die alarmiert werden dürfen.

Der Filter lässt sich später über "Konfigurieren" ändern.

### Wirkung des Filters

Ist ein Filter gesetzt, gilt strikt:

| Filter | `group_codes` im Aufruf | Ergebnis |
| --- | --- | --- |
| `G1,G2` | `G1` | wird alarmiert |
| `G1,G2` | `G1,G3` | Fehler, es wird nichts ausgelöst |
| `G1,G2` | nicht angegeben | Fehler, Gruppen müssen genannt werden |
| leer | beliebig | alles erlaubt |

Solange ein Filter gesetzt ist, ist `additional_msisdns` gesperrt — einzelne
Rufnummern würden den Filter sonst umgehen.

## Services

| Service | Wirkung |
| --- | --- |
| `blaulichtsms_alarm.trigger_alarm` | Alarm sofort auslösen |
| `blaulichtsms_alarm.send_info` | Info sofort senden |
| `blaulichtsms_alarm.create_appointment` | Termin für einen späteren Zeitpunkt |
| `blaulichtsms_alarm.query_alarm` | Daten eines Alarms samt Rückmeldungen |
| `blaulichtsms_alarm.list_alarms` | Alarme der Kundennummer auflisten |

### Beispiele

```yaml
action: blaulichtsms_alarm.trigger_alarm
data:
  alarm_text: "Brand B2, Hauptstraße 1"
  group_codes: ["G1", "G2"]
  needs_acknowledgement: true
  duration: 60
  address: "Hauptstraße 1, 7000 Eisenstadt"
```

```yaml
action: blaulichtsms_alarm.create_appointment
data:
  alarm_text: "Monatsschulung im Rüsthaus"
  start_date: "2026-10-01 18:00:00"
  group_codes: ["G1"]
```

Die auslösenden Services geben `alarm_id`, `result` und `alarm_data` zurück:

```yaml
actions:
  - action: blaulichtsms_alarm.trigger_alarm
    data:
      alarm_text: "Übung"
      group_codes: ["G1"]
    response_variable: alarm
  - action: persistent_notification.create
    data:
      message: "Alarm {{ alarm.alarm_id }} ausgelöst"
```

## Entität

`sensor.blaulichtsms_alarm_zuletzt_ausgeloester_alarm` zeigt den Zeitpunkt der
letzten Auslösung über diese Integration. Attribute: `alarm_id`, `alarm_text`,
`type`, `group_codes`, `result`. Der Wert übersteht einen Neustart.

## Entwicklung

`./dev.sh` legt die venv an, synchronisiert die Komponente nach `config/` und
startet Home Assistant im Container auf Port 8123.

```bash
uv run python -m ruff check          # Lint
uv run python -m unittest discover -v  # Tests
```

## Lizenz

Diese Software steht in keiner Verbindung zu blaulichtSMS. Lizenziert unter
[Apache License 2.0](LICENSE).
```

- [ ] **Step 2: `CLAUDE.md` schreiben**

```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Home Assistant custom integration (`custom_components/blaulichtsms_alarm/`) that
triggers blaulichtSMS alarms, infos and appointments through the
[Alarm API v1](https://github.com/blaulichtSMS/docs/blob/master/alarm_api_v1.md).
Distributed via HACS. The counterpart that *reads* alarms is the separate
`blaulichtsms` integration.

## Environment & Common Commands

The venv is managed with [`uv`](https://docs.astral.sh/uv/). Bootstrap with
`./dev.sh`. Run entry points via `uv run` — do not activate the venv manually.

```bash
uv run python -m ruff check                                              # lint
uv run python -m unittest discover -v                                    # all tests
uv run python -m unittest custom_components.blaulichtsms_alarm.test_api -v
```

No test touches the network. Async tests use `unittest.IsolatedAsyncioTestCase`,
`hass` is stubbed with `MagicMock`.

## Architecture

- `api.py` — `AlarmApiClient` plus the pure `build_trigger_payload`. No Home
  Assistant imports. The alarm API has no login endpoint; credentials go with
  every request. Non-OK `result` codes raise `BlaulichtSmsApiError`, credential
  related ones `BlaulichtSmsAuthError`.
- `group_filter.py` — pure functions. `parse_group_filter` splits the configured
  string, `resolve_group_codes` enforces it: with a filter set, group codes are
  mandatory and must all be inside the filter, otherwise nothing is triggered.
- `services.py` — five services. `trigger_alarm` (`type=alarm`), `send_info`
  (`type=info`), `create_appointment` (`type=info` + `startDate`), `query_alarm`
  and `list_alarms`. Registered once in `async_setup`. Handlers are module level
  coroutines so they can be tested without a running Home Assistant.
- `config_flow.py` — two step wizard (credentials, group filter) plus options,
  reauth and reconfigure. Credentials are validated with a read-only `list`
  call; it must never trigger an alarm.
- `__init__.py` — builds the client, verifies the credentials and stores
  `BlaulichtSmsAlarmRuntimeData` in `entry.runtime_data`. Nothing goes into
  `hass.data`.
- `sensor.py` — one restore-capable timestamp sensor, updated via dispatcher
  after every successful trigger.

Config-entry only: no YAML setup, no `PLATFORM_SCHEMA` — do not reintroduce it.

## Conventions

- Ruff config in `.ruff.toml`. Run it and fix everything before committing.
- `manifest.json` `version` is the single source of truth; `VERSION` in
  `const.py` reads it at import time.
- New `CONF_*` or service fields need entries in `strings.json`,
  `translations/en.json` and `translations/de.json`.
- Commits follow [Conventional Commits](https://www.conventionalcommits.org/).

## Release Process

Automated via release-please: pushes to `main` maintain a release PR that bumps
`manifest.json` and `CHANGELOG.md`; merging it tags the release and attaches the
zipped component for HACS. Do not hand-edit `CHANGELOG.md`, the `version` in
`manifest.json`, or `.release-please-manifest.json`.
```

- [ ] **Step 3: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: README und Projektleitfaden"
```

---

### Task 15: Gesamtverifikation

- [ ] **Step 1: Lint über das ganze Repo**

Run: `uv run python -m ruff check`
Expected: `All checks passed!`

- [ ] **Step 2: Alle Tests**

Run: `uv run python -m unittest discover -v`
Expected: `OK`, ca. 95 Tests, keine Fehler und keine Skips

- [ ] **Step 3: Manifest, hacs.json und services.yaml gegenlesen**

Run:
```bash
uv run python - <<'PY'
import json
from pathlib import Path
import yaml

base = Path("custom_components/blaulichtsms_alarm")
manifest = json.loads((base / "manifest.json").read_text())
assert manifest["domain"] == "blaulichtsms_alarm"
assert manifest["config_flow"] is True
assert json.loads(Path("hacs.json").read_text())["name"]
assert set(yaml.safe_load((base / "services.yaml").read_text())) == {
    "trigger_alarm",
    "send_info",
    "create_appointment",
    "query_alarm",
    "list_alarms",
}
print("manifest, hacs.json und services.yaml ok")
PY
```
Expected: `manifest, hacs.json und services.yaml ok`

- [ ] **Step 4: Integration in einer echten Home-Assistant-Instanz laden**

Run: `./dev.sh`
Expected: Home Assistant startet, das Log enthält keine Fehler zu
`blaulichtsms_alarm`. Unter Einstellungen → Geräte & Dienste lässt sich
"blaulichtSMS Alarm" hinzufügen und der Wizard zeigt beide Schritte. Unter
Entwicklerwerkzeuge → Aktionen erscheinen alle fünf Services mit deutschen
Beschriftungen.

- [ ] **Step 5: Abschluss-Commit, falls beim Test noch etwas angepasst wurde**

```bash
git status --short
```
Expected: leer, oder die Korrekturen werden als eigener `fix:`-Commit ergänzt.
