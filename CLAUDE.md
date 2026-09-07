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
