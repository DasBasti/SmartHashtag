"""Unit tests for select entity persistence."""

import pytest
import respx
from homeassistant.core import HomeAssistant
from pysmarthashtag.control.climate import HeatingLocation
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smarthashtag.const import DOMAIN


@pytest.mark.asyncio()
async def test_select_option_saves_to_config_entry(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """
    Test that selecting an option saves the value to config entry data.

    This verifies that when a user selects a heating level, the value is
    persisted to the config entry data using string keys (not enum objects).
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

    # Get the select entity for the steering wheel
    state = hass.states.get(
        "select.smart_testvin0000000001_conditioning_steering_wheel"
    )
    assert state
    assert state.state == "Off"

    # Select a new option
    await hass.services.async_call(
        "select",
        "select_option",
        {
            "entity_id": "select.smart_testvin0000000001_conditioning_steering_wheel",
            "option": "High",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify the value was saved to config entry data
    assert "selects" in entry.data
    # The key should be the string value of the HeatingLocation enum
    assert HeatingLocation.STEERING_WHEEL.value in entry.data["selects"]
    assert entry.data["selects"][HeatingLocation.STEERING_WHEEL.value] == 3


@pytest.mark.asyncio()
async def test_select_option_persists_after_reload(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """
    Test that select option values persist after simulated reload.

    This verifies that values stored with string keys can be read back
    after the entry is reloaded (simulating HA restart).
    """

    # Create entry with pre-existing select data (as it would be after persistence)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "sample_user",
            "password": "sample_password",
            "vehicle": "TestVIN0000000001",
            "selects": {
                HeatingLocation.DRIVER_SEAT.value: 2,  # "Mid"
                HeatingLocation.STEERING_WHEEL.value: 3,  # "High"
            },
        },
    )

    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Verify the select entity has the persisted value
    steering_state = hass.states.get(
        "select.smart_testvin0000000001_conditioning_steering_wheel"
    )
    assert steering_state
    assert steering_state.state == "High"

    driver_state = hass.states.get(
        "select.smart_testvin0000000001_conditioning_driver_seat"
    )
    assert driver_state
    assert driver_state.state == "Mid"


@pytest.mark.asyncio()
async def test_select_all_heating_locations(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """
    Test that all heating location select entities are created.
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

    # Check all heating location entities exist
    steering_state = hass.states.get(
        "select.smart_testvin0000000001_conditioning_steering_wheel"
    )
    assert steering_state is not None

    driver_state = hass.states.get(
        "select.smart_testvin0000000001_conditioning_driver_seat"
    )
    assert driver_state is not None

    passenger_state = hass.states.get(
        "select.smart_testvin0000000001_conditioning_passenger_seat"
    )
    assert passenger_state is not None


@pytest.mark.asyncio()
async def test_select_available_options(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """
    Test that select entities have correct available options.
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

    # Check options are correct
    steering_state = hass.states.get(
        "select.smart_testvin0000000001_conditioning_steering_wheel"
    )
    assert steering_state is not None
    options = steering_state.attributes.get("options")
    assert options == ["Off", "Low", "Mid", "High"]


@pytest.mark.asyncio()
async def test_select_cycling_through_options(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """
    Test cycling through all heating options.
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

    entity_id = "select.smart_testvin0000000001_conditioning_driver_seat"

    # Cycle through all options
    for option in ["Low", "Mid", "High", "Off"]:
        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": entity_id, "option": option},
            blocking=True,
        )
        await hass.async_block_till_done()

        state = hass.states.get(entity_id)
        assert state is not None
        # Verify the state reflects the selection
        expected_level = {"Off": 0, "Low": 1, "Mid": 2, "High": 3}[option]
        assert (
            entry.data["selects"][HeatingLocation.DRIVER_SEAT.value] == expected_level
        )
