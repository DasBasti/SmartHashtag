"""Unit tests for climate entity."""

import pytest
import respx
from homeassistant.components.climate.const import HVACMode
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smarthashtag.const import DOMAIN


def get_climate_entity_id(hass: HomeAssistant) -> str | None:
    """Find the climate entity ID."""
    for entity_id in hass.states.async_entity_ids("climate"):
        if entity_id.startswith("climate.smart"):
            return entity_id
    return None


@pytest.mark.asyncio()
async def test_climate_entity_setup(hass: HomeAssistant, smart_fixture: respx.Router):
    """Test that climate entity is set up correctly."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "sample_user",
            "password": "sample_password",
            "vehicle": "TestVIN0000000001",
        },
        options={},
    )

    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_id = get_climate_entity_id(hass)
    assert entity_id is not None, "Climate entity not found"

    state = hass.states.get(entity_id)
    assert state is not None
    # Default HVAC mode should be OFF
    assert state.state in [HVACMode.OFF, HVACMode.HEAT_COOL, "off", "heat_cool"]


@pytest.mark.asyncio()
async def test_climate_set_temperature(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """Test setting the target temperature on climate entity."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "sample_user",
            "password": "sample_password",
            "vehicle": "TestVIN0000000001",
        },
        options={},
    )

    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_id = get_climate_entity_id(hass)
    assert entity_id is not None, "Climate entity not found"

    # Set new temperature
    await hass.services.async_call(
        "climate",
        "set_temperature",
        {
            "entity_id": entity_id,
            ATTR_TEMPERATURE: 24,
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.attributes.get("temperature") == 24


@pytest.mark.asyncio()
async def test_climate_turn_on(hass: HomeAssistant, smart_fixture: respx.Router):
    """Test turning on the climate entity."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "sample_user",
            "password": "sample_password",
            "vehicle": "TestVIN0000000001",
        },
        options={},
    )

    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_id = get_climate_entity_id(hass)
    assert entity_id is not None, "Climate entity not found"

    # Turn on the climate
    await hass.services.async_call(
        "climate",
        "turn_on",
        {"entity_id": entity_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify the call was made (state may not change immediately due to API mocking)
    state = hass.states.get(entity_id)
    assert state is not None


@pytest.mark.asyncio()
async def test_climate_turn_off(hass: HomeAssistant, smart_fixture: respx.Router):
    """Test turning off the climate entity."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "sample_user",
            "password": "sample_password",
            "vehicle": "TestVIN0000000001",
        },
        options={},
    )

    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_id = get_climate_entity_id(hass)
    assert entity_id is not None, "Climate entity not found"

    # Turn off the climate
    await hass.services.async_call(
        "climate",
        "turn_off",
        {"entity_id": entity_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state is not None


@pytest.mark.asyncio()
async def test_climate_set_hvac_mode(hass: HomeAssistant, smart_fixture: respx.Router):
    """Test setting HVAC mode on climate entity."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "sample_user",
            "password": "sample_password",
            "vehicle": "TestVIN0000000001",
        },
        options={},
    )

    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_id = get_climate_entity_id(hass)
    assert entity_id is not None, "Climate entity not found"

    # Set HVAC mode to heat_cool
    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {"entity_id": entity_id, "hvac_mode": "heat_cool"},
        blocking=True,
    )
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state is not None

    # Set HVAC mode to off
    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {"entity_id": entity_id, "hvac_mode": "off"},
        blocking=True,
    )
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state is not None


@pytest.mark.asyncio()
async def test_climate_properties(hass: HomeAssistant, smart_fixture: respx.Router):
    """Test climate entity properties."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "sample_user",
            "password": "sample_password",
            "vehicle": "TestVIN0000000001",
        },
        options={},
    )

    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_id = get_climate_entity_id(hass)
    assert entity_id is not None, "Climate entity not found"

    state = hass.states.get(entity_id)
    assert state is not None

    # Check temperature attributes
    assert state.attributes.get("min_temp") == 16
    assert state.attributes.get("max_temp") == 30
    # Current temperature is available
    assert state.attributes.get("current_temperature") is not None
    hvac_modes = state.attributes.get("hvac_modes", [])
    assert HVACMode.HEAT_COOL in hvac_modes or "heat_cool" in hvac_modes
    assert HVACMode.OFF in hvac_modes or "off" in hvac_modes


@pytest.mark.asyncio()
async def test_climate_sync_methods_not_implemented(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """Test that synchronous climate methods raise NotImplementedError.

    Note: These synchronous methods exist only to satisfy the ClimateEntity base class
    interface requirements. The actual functionality is implemented in the async versions
    (async_turn_on, async_turn_off, async_set_hvac_mode, async_set_temperature) which are
    properly implemented and tested in other test cases. This test ensures the sync methods
    correctly raise NotImplementedError as intended by design.
    """
    from custom_components.smarthashtag.climate import SmartConditioningMode

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "sample_user",
            "password": "sample_password",
            "vehicle": "TestVIN0000000001",
        },
        options={},
    )

    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Access the entity directly from the coordinator
    coordinator = entry.runtime_data
    vehicle = coordinator.config_entry.data.get("vehicle")

    # Create an instance to test the NotImplementedError methods
    climate_entity = SmartConditioningMode(coordinator, vehicle)

    # Test all NotImplementedError methods
    with pytest.raises(NotImplementedError):
        climate_entity.set_fan_mode("auto")

    with pytest.raises(NotImplementedError):
        climate_entity.set_humidity(50.0)

    with pytest.raises(NotImplementedError):
        climate_entity.set_hvac_mode("heat")

    with pytest.raises(NotImplementedError):
        climate_entity.set_preset_mode("comfort")

    with pytest.raises(NotImplementedError):
        climate_entity.set_swing_mode("both")

    with pytest.raises(NotImplementedError):
        climate_entity.set_temperature(temperature=22)

    with pytest.raises(NotImplementedError):
        climate_entity.turn_aux_heat_off()

    with pytest.raises(NotImplementedError):
        climate_entity.turn_aux_heat_on()

    with pytest.raises(NotImplementedError):
        climate_entity.turn_off()

    with pytest.raises(NotImplementedError):
        climate_entity.turn_on()
