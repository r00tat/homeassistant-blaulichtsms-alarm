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
