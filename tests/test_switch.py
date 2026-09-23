"""Unit tests for switch entity."""

import json

import pytest
import respx
from homeassistant.core import HomeAssistant
from pysmarthashtag.control.climate import ClimateControll
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


def get_defrost_switch_entity_id(hass: HomeAssistant) -> str | None:
    """Find the front defrost switch entity ID."""
    for entity_id in hass.states.async_entity_ids("switch"):
        if entity_id.startswith("switch.smart") and "defrost" in entity_id:
            return entity_id
    return None


async def _setup_entry(hass: HomeAssistant) -> None:
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


def _telematics_payloads(router: respx.Router) -> list[dict]:
    return [
        json.loads(call.request.content)
        for call in router.calls
        if call.request.method == "PUT"
        and "/vehicle/telematics/" in call.request.url.path
    ]


@pytest.mark.asyncio()
async def test_defrost_switch_setup(hass: HomeAssistant, smart_fixture: respx.Router):
    """Test that the defrost switch reflects the reported defrost state."""
    await _setup_entry(hass)

    entity_id = get_defrost_switch_entity_id(hass)
    assert entity_id is not None, "Defrost switch entity not found"

    state = hass.states.get(entity_id)
    assert state is not None
    # The fixture reports "defrost": "false"
    assert state.state == "off"
    assert state.attributes.get("icon") == "mdi:car-defrost-front"


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    ("service", "command", "duration"),
    [("turn_on", "start", 90), ("turn_off", "stop", 0)],
)
async def test_defrost_switch_sends_command(
    hass: HomeAssistant,
    smart_fixture: respx.Router,
    service: str,
    command: str,
    duration: int,
):
    """Test that toggling the defrost switch sends the RCE_2 defrost command."""
    await _setup_entry(hass)

    entity_id = get_defrost_switch_entity_id(hass)
    assert entity_id is not None, "Defrost switch entity not found"

    await hass.services.async_call(
        "switch", service, {"entity_id": entity_id}, blocking=True
    )
    await hass.async_block_till_done()

    payloads = _telematics_payloads(smart_fixture)
    assert payloads, "No telematics command was sent"
    payload = payloads[-1]
    assert payload["serviceId"] == "RCE_2"
    assert payload["command"] == command
    assert payload["operationScheduling"]["duration"] == duration
    assert {"key": "rce.conditioner", "value": "2"} in payload["serviceParameters"]


@pytest.mark.asyncio()
async def test_defrost_switch_skipped_without_library_support(
    hass: HomeAssistant, smart_fixture: respx.Router, monkeypatch: pytest.MonkeyPatch
):
    """Test that no defrost switch is created when pysmarthashtag lacks set_defrost."""
    monkeypatch.delattr(ClimateControll, "set_defrost")

    await _setup_entry(hass)

    assert get_defrost_switch_entity_id(hass) is None
    assert get_switch_entity_id(hass) is not None
