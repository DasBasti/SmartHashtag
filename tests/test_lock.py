"""Unit tests for the door lock entity."""

import json
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
import respx
from homeassistant.components.lock import LockState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smarthashtag.const import DOMAIN, PENDING_STATE_TIMEOUT


async def _setup_entry(hass: HomeAssistant, vin: str = "TestVIN0000000001") -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "sample_user",
            "password": "sample_password",
            "vehicle": vin,
        },
        options={},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def get_lock_entity_id(hass: HomeAssistant) -> str | None:
    """Find the door lock entity ID."""
    for entity_id in hass.states.async_entity_ids("lock"):
        if entity_id.startswith("lock.smart") and "door_lock" in entity_id:
            return entity_id
    return None


def _telematics_payloads(router: respx.Router) -> list[dict]:
    """Return the JSON bodies of all telematics PUT requests."""
    return [
        json.loads(c.request.content)
        for c in router.calls
        if c.request.method == "PUT" and "/vehicle/telematics/" in c.request.url.path
    ]


async def _call_lock_service(hass: HomeAssistant, service: str, entity_id: str):
    await hass.services.async_call(
        "lock", service, {"entity_id": entity_id}, blocking=True
    )
    await hass.async_block_till_done()


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    ("vin", "expected"),
    [
        ("TestVIN0000000001", LockState.LOCKED),
        ("TestVIN0000000002", LockState.UNLOCKED),
    ],
)
async def test_lock_state_follows_central_locking(
    hass: HomeAssistant, smart_fixture: respx.Router, vin: str, expected: LockState
):
    """Test that the lock state reflects the reported central locking status."""
    await _setup_entry(hass, vin)

    entity_id = get_lock_entity_id(hass)
    assert entity_id is not None, "Lock entity not found"
    assert hass.states.get(entity_id).state == expected


@pytest.mark.asyncio()
async def test_unlock_sends_command_and_shows_unlocking(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """Test that unlocking sends RDU_2 and waits for the vehicle to confirm."""
    await _setup_entry(hass)
    entity_id = get_lock_entity_id(hass)

    await _call_lock_service(hass, "unlock", entity_id)

    payload = _telematics_payloads(smart_fixture)[-1]
    assert payload["serviceId"] == "RDU_2"
    assert payload["serviceParameters"] == [{"key": "door", "value": "all"}]
    assert hass.states.get(entity_id).state == LockState.UNLOCKING

    # The mocked vehicle still reports locked, so the command stays pending
    coordinator = hass.config_entries.async_entries(DOMAIN)[0].runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == LockState.UNLOCKING


@pytest.mark.asyncio()
async def test_lock_confirmed_by_vehicle(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """Test that the pending state clears once the vehicle reports it."""
    await _setup_entry(hass)
    entity_id = get_lock_entity_id(hass)
    coordinator = hass.config_entries.async_entries(DOMAIN)[0].runtime_data

    await _call_lock_service(hass, "lock", entity_id)

    payload = _telematics_payloads(smart_fixture)[-1]
    assert payload["serviceId"] == "RDL_2"
    assert payload["serviceParameters"] == [{"key": "door", "value": "all"}]
    assert hass.states.get(entity_id).state == LockState.LOCKING

    # The mocked vehicle reports locked, confirming the command
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == LockState.LOCKED


@pytest.mark.asyncio()
async def test_pending_state_times_out(
    hass: HomeAssistant, smart_fixture: respx.Router, freezer
):
    """Test that the reported state is shown again after the pending timeout."""
    await _setup_entry(hass)
    entity_id = get_lock_entity_id(hass)
    coordinator = hass.config_entries.async_entries(DOMAIN)[0].runtime_data

    await _call_lock_service(hass, "unlock", entity_id)
    assert hass.states.get(entity_id).state == LockState.UNLOCKING

    freezer.tick(timedelta(seconds=PENDING_STATE_TIMEOUT + 1))
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get(entity_id).state == LockState.LOCKED


@pytest.mark.asyncio()
async def test_rejected_command_raises(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """Test that a command the vehicle does not accept surfaces an error."""
    await _setup_entry(hass)
    entity_id = get_lock_entity_id(hass)

    with (
        patch(
            "pysmarthashtag.control.lock.DoorLockControl.unlock",
            new=AsyncMock(return_value=False),
        ),
        pytest.raises(HomeAssistantError),
    ):
        await _call_lock_service(hass, "unlock", entity_id)

    assert hass.states.get(entity_id).state == LockState.LOCKED
