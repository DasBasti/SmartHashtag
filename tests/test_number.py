"""Unit tests for the charging limit number entity."""

import json
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
import respx
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


def get_number_entity_id(hass: HomeAssistant) -> str | None:
    """Find the charging limit entity ID."""
    for entity_id in hass.states.async_entity_ids("number"):
        if entity_id.startswith("number.smart") and "charging_limit" in entity_id:
            return entity_id
    return None


def _telematics_payloads(router: respx.Router) -> list[dict]:
    """Return the JSON bodies of all telematics PUT requests."""
    return [
        json.loads(c.request.content)
        for c in router.calls
        if c.request.method == "PUT" and "/vehicle/telematics/" in c.request.url.path
    ]


async def _set_limit(hass: HomeAssistant, entity_id: str, value: float) -> None:
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": entity_id, "value": value},
        blocking=True,
    )
    await hass.async_block_till_done()


@pytest.mark.asyncio()
async def test_charging_limit_entity_setup(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """Test that the charging limit has the bounds of the vehicle."""
    await _setup_entry(hass)

    entity_id = get_number_entity_id(hass)
    assert entity_id is not None, "Charging limit entity not found"
    state = hass.states.get(entity_id)
    assert state.attributes["min"] == 50
    assert state.attributes["max"] == 100
    assert state.attributes["step"] == 5
    assert state.attributes["unit_of_measurement"] == "%"


@pytest.mark.asyncio()
async def test_set_charging_limit_sends_command(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """Test that the new limit is sent and shown until the vehicle confirms."""
    await _setup_entry(hass)
    entity_id = get_number_entity_id(hass)

    # Pick a value the mocked vehicle does not report, so it stays pending
    reported = float(hass.states.get(entity_id).state)
    value = 60 if reported != 60 else 65
    await _set_limit(hass, entity_id, value)

    payload = _telematics_payloads(smart_fixture)[-1]
    assert {"key": "soc", "value": str(value * 10)} in payload["serviceParameters"]
    assert float(hass.states.get(entity_id).state) == value


@pytest.mark.asyncio()
async def test_pending_limit_times_out(
    hass: HomeAssistant, smart_fixture: respx.Router, freezer
):
    """Test that the reported limit is shown again after the pending timeout."""
    await _setup_entry(hass)
    entity_id = get_number_entity_id(hass)
    coordinator = hass.config_entries.async_entries(DOMAIN)[0].runtime_data
    reported = float(hass.states.get(entity_id).state)
    value = 60 if reported != 60 else 65

    await _set_limit(hass, entity_id, value)
    assert float(hass.states.get(entity_id).state) == value

    freezer.tick(timedelta(seconds=PENDING_STATE_TIMEOUT + 1))
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert float(hass.states.get(entity_id).state) == reported


@pytest.mark.asyncio()
async def test_rejected_limit_raises(hass: HomeAssistant, smart_fixture: respx.Router):
    """Test that a limit the vehicle does not accept surfaces an error."""
    await _setup_entry(hass)
    entity_id = get_number_entity_id(hass)
    reported = hass.states.get(entity_id).state

    with (
        patch(
            "pysmarthashtag.control.charging.ChargingControl.set_charging_limit",
            new=AsyncMock(return_value=False),
        ),
        pytest.raises(HomeAssistantError),
    ):
        await _set_limit(hass, entity_id, 60)

    assert hass.states.get(entity_id).state == reported
