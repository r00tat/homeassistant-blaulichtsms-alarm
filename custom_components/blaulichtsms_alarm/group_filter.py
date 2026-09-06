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
