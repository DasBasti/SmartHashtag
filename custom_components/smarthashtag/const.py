"""Constants for Smart #1/#3 integration."""
from logging import getLogger
from logging import Logger
from typing import Final

LOGGER: Logger = getLogger(__package__)

# Base component constants
NAME = "Smart"
DOMAIN = "smarthashtag"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "0.2.0"

ATTRIBUTION = "Data provided by http://smart.com/"
ISSUE_URL = "https://github.com/DasBasti/SmartHashtag/issues"

# Icons
ICON = "mdi:car-electric"

# Platforms
SENSOR = "sensor"
PLATFORMS = [SENSOR]


# Configuration and options
CONF_ENABLED = "enabled"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# Defaults
DEFAULT_NAME = DOMAIN


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
