"""Unit tests for _handle_error function."""

import pytest
import respx
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smarthashtag.const import DOMAIN

SENSOR_TESTS = {
    "binary_sensor.smart_central_locking_status": {
        "device_class": "lock",
        "expected_value": "on",
    },
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
        assert state.state == SENSOR_TESTS[sensor_name]["expected_value"]
