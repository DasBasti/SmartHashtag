"""Unit tests for the trunk cover entity."""

import json
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
import respx
from homeassistant.components.cover import CoverState
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


def get_trunk_entity_id(hass: HomeAssistant) -> str | None:
    """Find the trunk cover entity ID."""
    for entity_id in hass.states.async_entity_ids("cover"):
        if entity_id.startswith("cover.smart") and "trunk" in entity_id:
            return entity_id
    return None


def _telematics_payloads(router: respx.Router) -> list[dict]:
    """Return the JSON bodies of all telematics PUT requests."""
    return [
        json.loads(c.request.content)
        for c in router.calls
        if c.request.method == "PUT" and "/vehicle/telematics/" in c.request.url.path
    ]


async def _call_cover_service(hass: HomeAssistant, service: str, entity_id: str):
    await hass.services.async_call(
        "cover", service, {"entity_id": entity_id}, blocking=True
    )
    await hass.async_block_till_done()


async def _refresh(hass: HomeAssistant) -> None:
    coordinator = hass.config_entries.async_entries(DOMAIN)[0].runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()


@pytest.mark.asyncio()
async def test_trunk_state_follows_open_status(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """Test that the trunk state reflects the reported trunk open status."""
    await _setup_entry(hass)

    entity_id = get_trunk_entity_id(hass)
    assert entity_id is not None, "Trunk entity not found"
    assert hass.states.get(entity_id).state == CoverState.CLOSED


@pytest.mark.asyncio()
async def test_open_trunk_sends_command_and_shows_opening(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """Test that opening sends RDU_2 for the trunk and waits for confirmation."""
    await _setup_entry(hass)
    entity_id = get_trunk_entity_id(hass)

    await _call_cover_service(hass, "open_cover", entity_id)

    payload = _telematics_payloads(smart_fixture)[-1]
    assert payload["serviceId"] == "RDU_2"
    assert payload["serviceParameters"] == [{"key": "target", "value": "trunk"}]
    assert hass.states.get(entity_id).state == CoverState.OPENING

    # The mocked vehicle still reports closed, so the command stays pending
    await _refresh(hass)
    assert hass.states.get(entity_id).state == CoverState.OPENING


@pytest.mark.asyncio()
async def test_close_trunk_confirmed_by_vehicle(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """Test that closing sends RDL_2 for the trunk and clears once confirmed."""
    await _setup_entry(hass)
    entity_id = get_trunk_entity_id(hass)

    await _call_cover_service(hass, "close_cover", entity_id)

    payload = _telematics_payloads(smart_fixture)[-1]
    assert payload["serviceId"] == "RDL_2"
    assert payload["serviceParameters"] == [{"key": "target", "value": "trunk"}]
    assert hass.states.get(entity_id).state == CoverState.CLOSING

    # The mocked vehicle reports closed, confirming the command
    await _refresh(hass)
    assert hass.states.get(entity_id).state == CoverState.CLOSED


@pytest.mark.asyncio()
async def test_pending_state_times_out(
    hass: HomeAssistant, smart_fixture: respx.Router, freezer
):
    """Test that the reported state is shown again after the pending timeout."""
    await _setup_entry(hass)
    entity_id = get_trunk_entity_id(hass)

    await _call_cover_service(hass, "open_cover", entity_id)
    assert hass.states.get(entity_id).state == CoverState.OPENING

    freezer.tick(timedelta(seconds=PENDING_STATE_TIMEOUT + 1))
    await _refresh(hass)

    assert hass.states.get(entity_id).state == CoverState.CLOSED


@pytest.mark.asyncio()
async def test_rejected_command_raises(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """Test that a command the vehicle does not accept surfaces an error."""
    await _setup_entry(hass)
    entity_id = get_trunk_entity_id(hass)

    with (
        patch(
            "pysmarthashtag.control.lock.DoorLockControl.open_trunk",
            new=AsyncMock(return_value=False),
        ),
        pytest.raises(HomeAssistantError),
    ):
        await _call_cover_service(hass, "open_cover", entity_id)

    assert hass.states.get(entity_id).state == CoverState.CLOSED
