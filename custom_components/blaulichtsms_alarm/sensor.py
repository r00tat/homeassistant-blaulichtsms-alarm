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
