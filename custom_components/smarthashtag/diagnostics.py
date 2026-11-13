"""Diagnostics support for the Smart #1/#3/#5 integration."""

from __future__ import annotations

import re
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from pysmarthashtag.api.log_sanitizer import sanitize_log_data

from . import SmartHashtagConfigEntry
from .const import CONF_VEHICLE

TO_REDACT = {
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_VEHICLE,
    "vin",
    "latitude",
    "longitude",
    "altitude",
    "start_position",
    "end_position",
    "trackpoints",
    "address",
    "token",
    "accessToken",
    "refreshToken",
}

VIN_PATTERN = re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b")


def _scrub_vins(data: Any) -> Any:
    """Recursively replace VINs found inside any string value."""
    if isinstance(data, dict):
        return {key: _scrub_vins(value) for key, value in data.items()}
    if isinstance(data, list):
        return [_scrub_vins(item) for item in data]
    if isinstance(data, str):
        return VIN_PATTERN.sub("**REDACTED**", data)
    return data


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SmartHashtagConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry, including raw vehicle API data."""
    coordinator = entry.runtime_data
    vehicles = getattr(coordinator.account, "vehicles", None) or {}

    vehicle_data: dict[str, Any] = {}
    for index, vehicle in enumerate(vehicles.values()):
        # Key by index so the VIN never appears as a dict key.
        vehicle_data[f"vehicle_{index}"] = _scrub_vins(
            async_redact_data(
                sanitize_log_data(getattr(vehicle, "data", {}) or {}), TO_REDACT
            )
        )

    return {
        "entry": async_redact_data(
            {"data": dict(entry.data), "options": dict(entry.options)}, TO_REDACT
        ),
        "last_update_success": coordinator.last_update_success,
        "update_interval": str(coordinator.update_interval),
        "vehicles": vehicle_data,
    }
