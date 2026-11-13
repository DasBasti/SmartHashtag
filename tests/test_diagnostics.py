"""Tests for the diagnostics download."""

from types import SimpleNamespace

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smarthashtag.const import DOMAIN
from custom_components.smarthashtag.diagnostics import (
    async_get_config_entry_diagnostics,
)

VIN = "HESXXXXXXXXXX1234"


async def test_diagnostics_redacts_sensitive_data(hass: HomeAssistant):
    """Credentials, VIN and location must not appear in the diagnostics."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"username": "me@example.com", "password": "secret", "vehicle": VIN},
    )
    vehicle = SimpleNamespace(
        data={
            "vin": VIN,
            "seriesCodeVs": "HC11",
            "position": {"latitude": 52.5, "longitude": 13.4},
            "note": f"car {VIN}",
        }
    )
    entry.runtime_data = SimpleNamespace(
        account=SimpleNamespace(vehicles={VIN: vehicle}),
        last_update_success=True,
        update_interval=None,
    )

    result = await async_get_config_entry_diagnostics(hass, entry)
    dumped = str(result)

    for secret in ("me@example.com", "secret", VIN, "52.5", "13.4"):
        assert secret not in dumped
    assert result["vehicles"]["vehicle_0"]["seriesCodeVs"] == "HC11"
