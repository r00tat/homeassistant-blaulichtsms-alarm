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
