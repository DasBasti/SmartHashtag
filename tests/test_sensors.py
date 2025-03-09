"""Unit tests for _handle_error function."""

from homeassistant.core import HomeAssistant
import pytest
import respx
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smarthashtag.const import DOMAIN
from custom_components.smarthashtag.sensor import remove_vin_from_key, vin_from_key


def test_remove_vin_from_key():
    """Test the remove_vin_from_key function.

    This function calls the remove_vin_from_key function with a sample key and checks that it returns the key with the VIN removed.
    """
    # Define the sample key
    key = "vin1234567890_odometer"

    # Call the function
    new_key = remove_vin_from_key(key)

    # Check that the returned key is correct
    assert new_key == "odometer"


def test_vin_from_key():
    """Test the vin_from_key function.

    This function calls the vin_from_key function with a sample key and checks that it returns the VIN from the key.
    """
    # Define the sample key
    key = "TestVIN0000000001_odometer"

    # Call the function
    vin = vin_from_key(key)

    # Check that the returned VIN is correct
    assert vin == "TestVIN0000000001"


@pytest.mark.asyncio()
async def test_sensor_updates(hass: HomeAssistant, smart_fixture: respx.Router):
    """
    Test the sensors function

    This loads a sample testing configuration from the pysmarthashtag package and checks that the sensors are updated correctly.
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

    state = hass.states.get("sensor.smart_last_update")

    assert state
    assert state.state == "2024-01-23T16:44:00+00:00"
