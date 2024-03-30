"""Constants for Smart #1/#3 integration."""
from logging import getLogger
from logging import Logger
from typing import Final

LOGGER: Logger = getLogger(__package__)

# Base component constants
NAME = "Smart"
DOMAIN = "smarthashtag"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "0.3.2"

ATTRIBUTION = "Data provided by http://smart.com/"
ISSUE_URL = "https://github.com/DasBasti/SmartHashtag/issues"

# Icons
ICON = "mdi:car-electric"

# Platforms
SENSOR = "sensor"
DEVICE_TRACKER = "device_tracker"
SWITCH = "switch"
CLIMATE = "climate"
PLATFORMS = [SENSOR, DEVICE_TRACKER, CLIMATE, SWITCH]


# Configuration and options
CONF_ENABLED = "enabled"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_CHARGING_INTERVAL = "charging_interval"
CONF_DRIVING_INTERVAL = "driving_interval"
CONF_CONDITIONING_TEMP = "conditioning_temp"
CONF_SEATHEATING_LEVEL = "seatheating_level"

# Defaults
DEFAULT_NAME = DOMAIN
DEFAULT_SCAN_INTERVAL = 300
DEFAULT_CHARGING_INTERVAL = 30
DEFAULT_DRIVING_INTERVAL = 60
MIN_SCAN_INTERVAL = 10
DEFAULT_CONDITIONING_TEMP = 21
DEFAULT_SEATHEATING_LEVEL = 3


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
