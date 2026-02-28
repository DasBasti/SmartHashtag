"""Constants for Smart #1/#3 integration."""

from logging import Logger, getLogger
from typing import Final

LOGGER: Logger = getLogger(__package__)

# Base component constants
NAME = "Smart"
DOMAIN = "smarthashtag"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "0.8.0-intl"

ATTRIBUTION = "Data provided by http://smart.com/"
ISSUE_URL = "https://github.com/DasBasti/SmartHashtag/issues"

# Icons
ICON = "mdi:car-electric"

# Platforms
SENSOR = "sensor"
DEVICE_TRACKER = "device_tracker"
SWITCH = "switch"
CLIMATE = "climate"
SELECT = "select"
PLATFORMS = [SENSOR, DEVICE_TRACKER, CLIMATE, SELECT, SWITCH]


# Configuration and options
CONF_ENABLED = "enabled"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_CHARGING_INTERVAL = "charging_interval"
CONF_DRIVING_INTERVAL = "driving_interval"
CONF_CONDITIONING_TEMP = "conditioning_temp"
CONF_SEATHEATING_LEVEL = "seatheating_level"
CONF_REGION = "region"
CONF_API_BASE_URL = "api_base_url"
CONF_API_BASE_URL_V2 = "api_base_url_v2"

# Defaults
DEFAULT_NAME = DOMAIN
DEFAULT_SCAN_INTERVAL = 300
DEFAULT_CHARGING_INTERVAL = 30
DEFAULT_DRIVING_INTERVAL = 60
FAST_INTERVAL = 5
MIN_SCAN_INTERVAL = 10
DEFAULT_CONDITIONING_TEMP = 21
DEFAULT_SEATHEATING_LEVEL = 3
DEFAULT_REGION = "eu"

# Region options
REGION_EU = "eu"
REGION_INTL = "intl"
REGION_CUSTOM = "custom"

REGIONS = {
    REGION_EU: "Europe (Hello Smart EU)",
    REGION_INTL: "International (Hello Smart International - Australia, Singapore, etc.)",
    REGION_CUSTOM: "Custom Endpoints",
}


STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is the Smart #1/#3 integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""

CONF_VEHICLE: Final = "vehicle"
CONF_VEHICLES: Final = "vehicles"
