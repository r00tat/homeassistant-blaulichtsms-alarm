"""Schemas and helpers for the blaulichtSMS Alarm config flow."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_CUSTOMER_ID,
    CONF_GROUP_FILTER,
    CONF_PASSWORD,
    CONF_USE_STAGING,
    CONF_USERNAME,
)
from .group_filter import parse_group_filter


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
            vol.Required(CONF_USERNAME, default=data.get(CONF_USERNAME, "")): cv.string,
            vol.Required(CONF_PASSWORD): cv.string,
            vol.Optional(
                CONF_USE_STAGING, default=data.get(CONF_USE_STAGING, False)
            ): cv.boolean,
        }
    )


def group_options(
    selected: list[str], groups: dict[str, str] | None = None
) -> list[SelectOptionDict]:
    """Return the selectable alarm groups, discovered ones first.

    Already configured group codes are appended so a filter survives a
    reconfiguration even when the group was not alerted recently and therefore
    missing from the suggestions.
    """
    groups = groups or {}
    codes = list(groups) + [code for code in selected if code not in groups]
    return [
        SelectOptionDict(
            value=code,
            label=code
            if groups.get(code, code) == code
            else f"{code} – {groups[code]}",
        )
        for code in codes
    ]


def groups_schema(
    data: dict[str, Any] | None = None, groups: dict[str, str] | None = None
) -> vol.Schema:
    """Return the schema of the group filter step.

    The alarm groups discovered from recent alarms are offered as options, but
    custom values stay allowed: the API cannot list all configured groups, so
    the suggestions are never guaranteed to be complete.
    """
    data = data or {}
    selected = parse_group_filter(data.get(CONF_GROUP_FILTER))
    return vol.Schema(
        {
            vol.Optional(CONF_GROUP_FILTER, default=selected): SelectSelector(
                SelectSelectorConfig(
                    options=group_options(selected, groups),
                    multiple=True,
                    custom_value=True,
                    mode=SelectSelectorMode.DROPDOWN,
                    sort=False,
                )
            ),
        }
    )


def reauth_schema(data: dict[str, Any] | None = None) -> vol.Schema:
    """Return the schema of the reauth step."""
    data = data or {}
    return vol.Schema(
        {
            vol.Required(CONF_USERNAME, default=data.get(CONF_USERNAME, "")): cv.string,
            vol.Required(CONF_PASSWORD): cv.string,
        }
    )
