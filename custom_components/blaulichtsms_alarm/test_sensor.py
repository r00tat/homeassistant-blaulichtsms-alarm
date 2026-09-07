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
