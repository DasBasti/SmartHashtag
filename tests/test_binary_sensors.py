"""Unit tests for _handle_error function."""

import pytest
import respx
from homeassistant.core import HomeAssistant
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
