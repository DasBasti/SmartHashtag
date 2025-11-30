"""Unit tests for _handle_error function."""

import pytest
import respx
from homeassistant.core import HomeAssistant
from httpx import Request, Response
from pysmarthashtag.tests import RESPONSE_DIR, load_response
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smarthashtag.const import DOMAIN

# On means open (unlocked), Off means closed (locked)
SENSOR_TESTS = {
    "binary_sensor.smart_central_locking_status": {
        "device_class": "lock",
        "expected_value": "off",
    },
    #    "binary_sensor.door_lock_status_driver": {
    #        "device_class": "lock",
    #        "expected_value": "off",
    #    },
    #    "binary_sensor.oor_lock_status_driver_rear": {
    #        "device_class": "lock",
    #        "expected_value": "off",
    #    },
    #    "binary_sensor.door_lock_status_passenger": {
    #        "device_class": "lock",
    #        "expected_value": "off",
    #    },
    #    "binary_sensor.door_open_status_driver": {
    #        "device_class": "door",
    #        "expected_value": "off",
    #    },
    #    "binary_sensor.door_open_status_driver_rear": {
    #        "device_class": "door",
    #        "expected_value": "off",
    #    },
    #    "binary_sensor.door_open_status_passenger": {
    #        "device_class": "door",
    #        "expected_value": "off",
    #    },
    #    "binary_sensor.door_open_status_passenger_rear": {
    #        "device_class": "door",
    #        "expected_value": "off",
    #    },
    #    "binary_sensor.engine_hood_open_status": {
    #        "device_class": "door",
    #        "expected_value": "off",
    #    },
    #    "binary_sensor.electric_park_brake_status": {
    #        "device_class": "door",
    #        "expected_value": "off",
    #    },
    #    "binary_sensor.trunk_lock_status": {
    #        "device_class": "lock",
    #        "expected_value": "off",
    #    },
    "binary_sensor.smart_trunk_open_status": {
        "device_class": "door",
        "expected_value": "off",
    },
}


@pytest.mark.asyncio()
async def test_binary_sensors(hass: HomeAssistant, smart_fixture: respx.Router):
    """
    Test the binary sensors according to https://github.com/DasBasti/SmartHashtag/issues/222

    This loads a sample testing configuration from the pysmarthashtag package and checks that the binary sensors have the expcted values.
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
    await entry.runtime_data.async_refresh()

    for sensor_name in SENSOR_TESTS:
        state = hass.states.get(sensor_name)

        assert state
        assert (
            state.attributes["device_class"]
            == SENSOR_TESTS[sensor_name]["device_class"]
        )
        assert (
            sensor_name + ":" + state.state
            == sensor_name + ":" + SENSOR_TESTS[sensor_name]["expected_value"]
        )


@pytest.mark.asyncio()
async def test_binary_sensor_updates(hass: HomeAssistant, smart_fixture: respx.Router):
    """
    Test that binary sensor values update when coordinator data changes.

    This test verifies the fix for https://github.com/DasBasti/SmartHashtag/issues/262
    where the central locking binary sensor stayed in locked state even when raw logs
    showed values changing between 0 and 1.

    The issue was caused by using @cached_property instead of @property,
    which cached the value and prevented updates.
    """
    # Track the central locking status value to toggle between locked (1/2) and unlocked (0)
    central_locking_value = "2"  # Initial locked state

    async def toggle_central_locking(request: Request, route: respx.Route) -> Response:
        nonlocal central_locking_value
        response = load_response(RESPONSE_DIR / "vehicle_info.json")
        response["data"]["vehicleStatus"]["additionalVehicleStatus"][
            "drivingSafetyStatus"
        ]["centralLockingStatus"] = central_locking_value
        return Response(200, json=response)

    smart_fixture.get(
        "https://api.ecloudeu.com/remote-control/vehicle/status/TestVIN0000000001?latest=True&target=basic%2Cmore&userId=112233",
    ).mock(side_effect=toggle_central_locking)

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

    # Initial state should be "off" (locked) because centralLockingStatus = "2"
    # is_on_fn returns True when central_locking_status == 0 (unlocked)
    # HA binary_sensor: on = True (unlocked), off = False (locked)
    state = hass.states.get("binary_sensor.smart_central_locking_status")
    assert state
    assert state.state == "off"  # Locked

    # Now change to unlocked (centralLockingStatus = "0")
    central_locking_value = "0"
    await entry.runtime_data.async_refresh()

    # State should now be "on" (unlocked)
    state = hass.states.get("binary_sensor.smart_central_locking_status")
    assert state
    assert state.state == "on"  # Unlocked

    # Change back to locked (centralLockingStatus = "1")
    central_locking_value = "1"
    await entry.runtime_data.async_refresh()

    # State should be "off" (locked) again
    state = hass.states.get("binary_sensor.smart_central_locking_status")
    assert state
    assert state.state == "off"  # Locked
