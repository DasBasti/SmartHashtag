"""Unit tests for the window ventilation and sunshade switches."""

import json
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
import respx
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smarthashtag.const import DOMAIN, PENDING_STATE_TIMEOUT


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


def _find_switch(hass: HomeAssistant, name: str) -> str | None:
    for entity_id in hass.states.async_entity_ids("switch"):
        if entity_id.startswith("switch.smart") and name in entity_id:
            return entity_id
    return None


def _telematics_payloads(router: respx.Router) -> list[dict]:
    return [
        json.loads(call.request.content)
        for call in router.calls
        if call.request.method == "PUT"
        and "/vehicle/telematics/" in call.request.url.path
    ]


async def _call(hass: HomeAssistant, service: str, entity_id: str) -> None:
    await hass.services.async_call(
        "switch", service, {"entity_id": entity_id}, blocking=True
    )
    await hass.async_block_till_done()


@pytest.mark.asyncio()
async def test_sunshade_switch_follows_reported_state(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """Test that the sunshade switch reflects the reported curtain state."""
    await _setup_entry(hass)

    entity_id = _find_switch(hass, "sunshade")
    assert entity_id is not None, "Sunshade switch entity not found"
    # The fixture reports "curtainOpenStatus": "1"
    assert hass.states.get(entity_id).state == "on"


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    ("name", "target"),
    [("sunshade", "sunshade"), ("window_ventilation", "ventilate")],
)
@pytest.mark.parametrize(
    ("service", "command"), [("turn_on", "start"), ("turn_off", "stop")]
)
async def test_switch_sends_rws_command(
    hass: HomeAssistant,
    smart_fixture: respx.Router,
    name: str,
    target: str,
    service: str,
    command: str,
):
    """Test that the switches send the RWS_2 command with the right target."""
    await _setup_entry(hass)
    entity_id = _find_switch(hass, name)
    assert entity_id is not None, f"{name} switch entity not found"

    await _call(hass, service, entity_id)

    payload = _telematics_payloads(smart_fixture)[-1]
    assert payload["serviceId"] == "RWS_2"
    assert payload["command"] == command
    assert payload["serviceParameters"] == [{"key": "target", "value": target}]


@pytest.mark.asyncio()
async def test_sunshade_holds_requested_state_until_timeout(
    hass: HomeAssistant, smart_fixture: respx.Router, freezer
):
    """Test that the requested state is shown until the pending timeout."""
    await _setup_entry(hass)
    entity_id = _find_switch(hass, "sunshade")
    coordinator = hass.config_entries.async_entries(DOMAIN)[0].runtime_data

    await _call(hass, "turn_off", entity_id)
    assert hass.states.get(entity_id).state == "off"

    # The vehicle still reports the sunshade as open
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "off"

    freezer.tick(timedelta(seconds=PENDING_STATE_TIMEOUT + 1))
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "on"


@pytest.mark.asyncio()
async def test_window_ventilation_assumes_last_requested_state(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """Test that the ventilation state is unknown until a command was sent."""
    await _setup_entry(hass)
    entity_id = _find_switch(hass, "window_ventilation")
    coordinator = hass.config_entries.async_entries(DOMAIN)[0].runtime_data

    state = hass.states.get(entity_id)
    assert state.state == "unknown"
    assert state.attributes["assumed_state"] is True

    await _call(hass, "turn_on", entity_id)
    assert hass.states.get(entity_id).state == "on"

    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "on"

    await _call(hass, "turn_off", entity_id)
    assert hass.states.get(entity_id).state == "off"


@pytest.mark.asyncio()
async def test_rejected_command_raises(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """Test that a command the vehicle does not accept surfaces an error."""
    await _setup_entry(hass)
    entity_id = _find_switch(hass, "window_ventilation")

    with (
        patch(
            "pysmarthashtag.control.windows.WindowControl.set_ventilation",
            new=AsyncMock(return_value=False),
        ),
        pytest.raises(HomeAssistantError),
    ):
        await _call(hass, "turn_on", entity_id)

    assert hass.states.get(entity_id).state == "unknown"
