"""Unit tests for switch entity."""

import json
from datetime import timedelta

import pytest
import respx
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pysmarthashtag.control.climate import ClimateControll
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smarthashtag.const import DOMAIN, PENDING_STATE_TIMEOUT


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


def _defrost_switch_setup(hass: HomeAssistant):
    """Return the coordinator and vehicle behind the defrost switch."""
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    coordinator = entry.runtime_data
    return coordinator, coordinator.account.vehicles["TestVIN0000000001"]


@pytest.mark.asyncio()
async def test_defrost_switch_holds_requested_state_until_vehicle_confirms(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """Test that the switch does not flip back while the vehicle lags behind."""
    await _setup_entry(hass)
    entity_id = get_defrost_switch_entity_id(hass)
    coordinator, vehicle = _defrost_switch_setup(hass)

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )
    await hass.async_block_till_done()

    # The vehicle still reports "defrost": "false" after the refresh
    assert vehicle.climate.defrosting_active is False
    assert hass.states.get(entity_id).state == "on"
    assert "defrost_switch" in coordinator._update_intervals

    # Once the vehicle confirms, the switch follows the reported state again
    vehicle.climate.defrosting_active = True
    coordinator.async_update_listeners()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "on"
    assert "defrost_switch" not in coordinator._update_intervals

    vehicle.climate.defrosting_active = False
    coordinator.async_update_listeners()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "off"


@pytest.mark.asyncio()
async def test_defrost_switch_falls_back_after_timeout(
    hass: HomeAssistant, smart_fixture: respx.Router, freezer
):
    """Test that the reported state wins once the pending timeout expires."""
    await _setup_entry(hass)
    entity_id = get_defrost_switch_entity_id(hass)
    coordinator, _ = _defrost_switch_setup(hass)

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "on"

    freezer.tick(timedelta(seconds=PENDING_STATE_TIMEOUT - 1))
    coordinator.async_update_listeners()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "on"

    freezer.tick(timedelta(seconds=2))
    coordinator.async_update_listeners()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "off"
    assert "defrost_switch" not in coordinator._update_intervals


@pytest.mark.asyncio()
async def test_defrost_switch_keeps_reported_state_when_command_fails(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """Test that a rejected command does not show the requested state."""
    await _setup_entry(hass)
    entity_id = get_defrost_switch_entity_id(hass)
    coordinator, vehicle = _defrost_switch_setup(hass)

    async def _rejected(active: bool) -> bool:
        return False

    vehicle.climate_control.set_defrost = _rejected

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )
    await hass.async_block_till_done()

    assert hass.states.get(entity_id).state == "off"
    assert "defrost_switch" not in coordinator._update_intervals


async def _setup_entry_with_selects(hass: HomeAssistant, selects: dict) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "sample_user",
            "password": "sample_password",
            "vehicle": "TestVIN0000000001",
            "selects": selects,
        },
        options={},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def get_heating_switch_entity_id(hass: HomeAssistant, key: str) -> str | None:
    """Find a heating switch by its unique id suffix."""
    registry = er.async_get(hass)
    for entity in registry.entities.values():
        if entity.domain == "switch" and entity.unique_id.endswith(f"_{key}_switch"):
            return entity.entity_id
    return None


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    ("key", "selects", "expected"),
    [
        # Uses the levels from the selects, skips locations set to "Off"
        (
            "seat_heating",
            {"front-left": 2, "front-right": 0, "steering_wheel": 3},
            [
                {"key": "rce.heat", "value": "front-left"},
                {"key": "rce.level", "value": "2"},
            ],
        ),
        # All selects "Off": falls back to the default level for every location
        (
            "seat_heating",
            {},
            [
                {"key": "rce.heat", "value": "front-left"},
                {"key": "rce.level", "value": "3"},
                {"key": "rce.heat", "value": "front-right"},
                {"key": "rce.level", "value": "3"},
            ],
        ),
        (
            "steering_wheel_heating",
            {"front-left": 2, "steering_wheel": 1},
            [
                {"key": "rce.heat", "value": "steering_wheel"},
                {"key": "rce.level", "value": "1"},
            ],
        ),
    ],
)
async def test_heating_switch_turn_on_sends_heat_only(
    hass: HomeAssistant,
    smart_fixture: respx.Router,
    key: str,
    selects: dict,
    expected: list[dict],
):
    """Test that a heating switch starts heating without climate conditioning."""
    await _setup_entry_with_selects(hass, selects)
    entity_id = get_heating_switch_entity_id(hass, key)
    assert entity_id is not None, f"{key} switch entity not found"
    assert hass.states.get(entity_id).state == "off"

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )
    await hass.async_block_till_done()

    payload = _telematics_payloads(smart_fixture)[-1]
    assert payload["serviceId"] == "RCE_2"
    assert payload["command"] == "start"
    assert payload["serviceParameters"] == expected
    assert hass.states.get(entity_id).state == "on"


@pytest.mark.asyncio()
async def test_heating_switch_turn_off_sends_stop(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """Test that turning a heating switch off stops all its locations."""
    await _setup_entry_with_selects(hass, {"front-left": 2})
    entity_id = get_heating_switch_entity_id(hass, "seat_heating")

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": entity_id}, blocking=True
    )
    await hass.async_block_till_done()

    payload = _telematics_payloads(smart_fixture)[-1]
    assert payload["command"] == "stop"
    assert payload["serviceParameters"] == [
        {"key": "rce.heat", "value": "front-left"},
        {"key": "rce.heat", "value": "front-right"},
        {"key": "rce.level", "value": "0"},
    ]


@pytest.mark.asyncio()
async def test_seat_heating_switch_follows_reported_state(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """Test that the seat heating switch is on when either front seat heats."""
    await _setup_entry_with_selects(hass, {})
    entity_id = get_heating_switch_entity_id(hass, "seat_heating")
    coordinator, vehicle = _defrost_switch_setup(hass)

    vehicle.climate.driver_heating_status = False
    vehicle.climate.passenger_heating_status = True
    coordinator.async_update_listeners()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "on"

    vehicle.climate.passenger_heating_status = False
    coordinator.async_update_listeners()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "off"


@pytest.mark.asyncio()
async def test_heating_switches_skipped_without_library_support(
    hass: HomeAssistant, smart_fixture: respx.Router, monkeypatch: pytest.MonkeyPatch
):
    """Test that no heating switches are created when pysmarthashtag lacks set_heating."""
    monkeypatch.delattr(ClimateControll, "set_heating")

    await _setup_entry(hass)

    assert get_heating_switch_entity_id(hass, "seat_heating") is None
    assert get_heating_switch_entity_id(hass, "steering_wheel_heating") is None
    assert get_defrost_switch_entity_id(hass) is not None
