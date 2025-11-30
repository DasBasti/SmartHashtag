"""Unit tests for device tracker."""

import pytest
import respx
from homeassistant.core import HomeAssistant
from httpx import Request, Response
from pysmarthashtag.tests import RESPONSE_DIR, load_response
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smarthashtag.const import DOMAIN


def get_device_tracker_entity_id(hass: HomeAssistant) -> str | None:
    """Find the device tracker entity ID."""
    for entity_id in hass.states.async_entity_ids("device_tracker"):
        if entity_id.startswith("device_tracker.smart"):
            return entity_id
    return None


@pytest.mark.asyncio()
async def test_device_tracker_uses_coordinator_data(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """
    Test that device tracker gets position data from coordinator.

    This test verifies that the device tracker correctly reads position data
    from self.coordinator.data instead of making separate API calls.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "sample_user",
            "password": "sample_password",
            "vehicle": "TestVIN0000000001",
        },
    )

    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Find the device tracker entity
    entity_id = get_device_tracker_entity_id(hass)
    assert entity_id is not None, "Device tracker entity not found"

    state = hass.states.get(entity_id)

    assert state
    # Position values from test fixture divided by 3600000
    # latitude: 123456789 / 3600000 = 34.293552
    # longitude: 987654321 / 3600000 = 274.348422
    assert float(state.attributes.get("latitude")) == pytest.approx(34.293552, rel=1e-5)
    assert float(state.attributes.get("longitude")) == pytest.approx(
        274.348422, rel=1e-5
    )
    # Altitude is a ValueWithUnit object
    altitude = state.attributes.get("altitude")
    assert altitude.value == 105
    assert state.attributes.get("position_can_be_trusted") is True


@pytest.mark.asyncio()
async def test_device_tracker_updates_with_coordinator(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """
    Test that device tracker updates when coordinator refreshes.

    This test verifies that position data is updated when the coordinator
    fetches new data from the API.
    """
    position_values = {"latitude": "123456789", "longitude": "987654321"}

    async def update_position(request: Request, route: respx.Route) -> Response:
        response = load_response(RESPONSE_DIR / "vehicle_info.json")
        response["data"]["vehicleStatus"]["basicVehicleStatus"]["position"][
            "latitude"
        ] = position_values["latitude"]
        response["data"]["vehicleStatus"]["basicVehicleStatus"]["position"][
            "longitude"
        ] = position_values["longitude"]
        return Response(200, json=response)

    smart_fixture.get(
        "https://api.ecloudeu.com/remote-control/vehicle/status/TestVIN0000000001?latest=True&target=basic%2Cmore&userId=112233",
    ).mock(side_effect=update_position)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "sample_user",
            "password": "sample_password",
            "vehicle": "TestVIN0000000001",
        },
    )

    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Find the device tracker entity
    entity_id = get_device_tracker_entity_id(hass)
    assert entity_id is not None, "Device tracker entity not found"

    # Initial position
    state = hass.states.get(entity_id)
    assert state
    initial_lat = float(state.attributes.get("latitude"))
    initial_lon = float(state.attributes.get("longitude"))

    # Update position values
    position_values["latitude"] = "180000000"  # 50.0 degrees
    position_values["longitude"] = "360000000"  # 100.0 degrees

    # Refresh coordinator to get new data
    await entry.runtime_data.async_refresh()

    # Verify position updated
    state = hass.states.get(entity_id)
    assert state
    new_lat = float(state.attributes.get("latitude"))
    new_lon = float(state.attributes.get("longitude"))

    # Position should have changed
    assert new_lat != initial_lat
    assert new_lon != initial_lon
    assert new_lat == pytest.approx(50.0, rel=1e-5)
    assert new_lon == pytest.approx(100.0, rel=1e-5)
