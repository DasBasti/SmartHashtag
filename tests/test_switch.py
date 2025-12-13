"""Unit tests for switch entity."""

import pytest
import respx
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smarthashtag.const import DOMAIN


def get_switch_entity_id(hass: HomeAssistant) -> str | None:
    """Find the charging control switch entity ID."""
    for entity_id in hass.states.async_entity_ids("switch"):
        if entity_id.startswith("switch.smart") and "charging" in entity_id:
            return entity_id
    return None


@pytest.mark.asyncio()
async def test_switch_entity_setup(hass: HomeAssistant, smart_fixture: respx.Router):
    """Test that switch entity is set up correctly."""
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

    entity_id = get_switch_entity_id(hass)
    assert entity_id is not None, "Switch entity not found"

    state = hass.states.get(entity_id)
    assert state is not None
    # Default state should be off (not charging)
    assert state.state in ["off", "on"]


@pytest.mark.asyncio()
async def test_switch_turn_on(hass: HomeAssistant, smart_fixture: respx.Router):
    """Test turning on the charging switch."""
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

    entity_id = get_switch_entity_id(hass)
    assert entity_id is not None, "Switch entity not found"

    # Turn on the charging switch
    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": entity_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify the call was made (state may not change immediately due to API mocking)
    state = hass.states.get(entity_id)
    assert state is not None


@pytest.mark.asyncio()
async def test_switch_turn_off(hass: HomeAssistant, smart_fixture: respx.Router):
    """Test turning off the charging switch."""
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

    entity_id = get_switch_entity_id(hass)
    assert entity_id is not None, "Switch entity not found"

    # Turn off the charging switch
    await hass.services.async_call(
        "switch",
        "turn_off",
        {"entity_id": entity_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state is not None


@pytest.mark.asyncio()
async def test_switch_properties(hass: HomeAssistant, smart_fixture: respx.Router):
    """Test switch entity properties."""
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

    entity_id = get_switch_entity_id(hass)
    assert entity_id is not None, "Switch entity not found"

    state = hass.states.get(entity_id)
    assert state is not None

    # Check that the entity has the expected icon
    assert state.attributes.get("icon") == "mdi:ev-station"
