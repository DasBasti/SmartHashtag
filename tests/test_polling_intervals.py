"""Tests that fast polling after commands and while charging/driving ends again."""

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
import respx
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pysmarthashtag.models import ValueWithUnit
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smarthashtag.const import (
    CONF_CHARGING_INTERVAL,
    CONF_DRIVING_INTERVAL,
    DOMAIN,
    PENDING_STATE_TIMEOUT,
)

VIN = "TestVIN0000000001"


async def _setup_entry(hass: HomeAssistant, options: dict | None = None):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "sample_user",
            "password": "sample_password",
            "vehicle": VIN,
        },
        options=options or {},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coordinator = entry.runtime_data
    return coordinator, coordinator.account.vehicles[VIN]


def _entity_id(hass: HomeAssistant, domain: str, contains: str) -> str:
    for entity_id in hass.states.async_entity_ids(domain):
        if entity_id.startswith(f"{domain}.smart") and contains in entity_id:
            return entity_id
    raise AssertionError(f"No {domain} entity containing {contains!r}")


# --- Charging switch ---------------------------------------------------------


@pytest.mark.asyncio()
async def test_charging_switch_fast_polling_ends_when_vehicle_confirms(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """Fast polling after a charging command must stop once the car reports it."""
    coordinator, vehicle = await _setup_entry(hass)
    entity_id = _entity_id(hass, "switch", "charging")
    vehicle.battery.charging_status = "NOT_CHARGING"
    coordinator.async_update_listeners()
    await hass.async_block_till_done()

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )
    await hass.async_block_till_done()

    assert hass.states.get(entity_id).state == "on"
    assert "charging_switch" in coordinator._update_intervals

    vehicle.battery.charging_status = "CHARGING"
    coordinator.async_update_listeners()
    await hass.async_block_till_done()

    assert hass.states.get(entity_id).state == "on"
    assert "charging_switch" not in coordinator._update_intervals


@pytest.mark.asyncio()
async def test_charging_switch_fast_polling_ends_after_timeout(
    hass: HomeAssistant, smart_fixture: respx.Router, freezer
):
    """Fast polling must stop even if the car never reports the new state."""
    coordinator, vehicle = await _setup_entry(hass)
    entity_id = _entity_id(hass, "switch", "charging")
    vehicle.battery.charging_status = "NOT_CHARGING"

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )
    await hass.async_block_till_done()
    assert "charging_switch" in coordinator._update_intervals

    freezer.tick(timedelta(seconds=PENDING_STATE_TIMEOUT + 1))
    coordinator.async_update_listeners()
    await hass.async_block_till_done()

    assert hass.states.get(entity_id).state == "off"
    assert "charging_switch" not in coordinator._update_intervals


# --- Climate -----------------------------------------------------------------


@pytest.mark.asyncio()
async def test_climate_fast_polling_ends_when_preconditioning_stops_by_itself(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """The car ending preconditioning on its own must not leave fast polling on."""
    coordinator, vehicle = await _setup_entry(hass)
    entity_id = _entity_id(hass, "climate", "")
    vehicle.climate.pre_climate_active = False

    await hass.services.async_call(
        "climate", "turn_on", {"entity_id": entity_id}, blocking=True
    )
    await hass.async_block_till_done()

    assert hass.states.get(entity_id).state == "heat_cool"
    assert "climate" in coordinator._update_intervals

    # The vehicle confirms
    vehicle.climate.pre_climate_active = True
    coordinator.async_update_listeners()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "heat_cool"
    assert "climate" not in coordinator._update_intervals

    # The preconditioning timer in the car runs out
    vehicle.climate.pre_climate_active = False
    coordinator.async_update_listeners()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "off"
    assert "climate" not in coordinator._update_intervals


@pytest.mark.asyncio()
async def test_climate_fast_polling_ends_after_timeout(
    hass: HomeAssistant, smart_fixture: respx.Router, freezer
):
    """Fast polling must stop even if the car never starts preconditioning."""
    coordinator, vehicle = await _setup_entry(hass)
    entity_id = _entity_id(hass, "climate", "")
    vehicle.climate.pre_climate_active = False

    await hass.services.async_call(
        "climate", "turn_on", {"entity_id": entity_id}, blocking=True
    )
    await hass.async_block_till_done()
    assert "climate" in coordinator._update_intervals

    freezer.tick(timedelta(seconds=PENDING_STATE_TIMEOUT - 1))
    coordinator.async_update_listeners()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "heat_cool"
    assert "climate" in coordinator._update_intervals

    freezer.tick(timedelta(seconds=2))
    coordinator.async_update_listeners()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "off"
    assert "climate" not in coordinator._update_intervals


@pytest.mark.asyncio()
async def test_climate_rejected_command_raises_and_does_not_poll_fast(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """A command the car rejects is reported and does not start fast polling."""
    coordinator, vehicle = await _setup_entry(hass)
    entity_id = _entity_id(hass, "climate", "")
    vehicle.climate.pre_climate_active = False

    async def _rejected(temp, active):
        return False

    vehicle.climate_control.set_climate_conditioning = _rejected

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "climate", "turn_on", {"entity_id": entity_id}, blocking=True
        )
    await hass.async_block_till_done()

    assert hass.states.get(entity_id).state == "off"
    assert "climate" not in coordinator._update_intervals


# --- Charging / driving intervals ---------------------------------------------


@pytest.mark.asyncio()
async def test_charging_interval_follows_charging_current(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """The configured charging interval applies while current flows, then resets."""
    coordinator, vehicle = await _setup_entry(
        hass, options={CONF_CHARGING_INTERVAL: 45}
    )

    vehicle.battery.charging_current = ValueWithUnit(16.0, "A")
    coordinator._update_activity_intervals()
    assert coordinator._update_intervals["charging"] == timedelta(seconds=45)
    assert coordinator.update_interval == timedelta(seconds=45)

    vehicle.battery.charging_current = ValueWithUnit(0.0, "A")
    coordinator._update_activity_intervals()
    assert "charging" not in coordinator._update_intervals


@pytest.mark.asyncio()
async def test_unknown_charging_current_is_not_charging(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """A missing charging current must not switch to the charging interval."""
    coordinator, vehicle = await _setup_entry(hass)

    vehicle.battery.charging_current = ValueWithUnit(None, None)
    coordinator._update_activity_intervals()
    assert "charging" not in coordinator._update_intervals


@pytest.mark.asyncio()
async def test_driving_interval_follows_engine_state(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """The configured driving interval applies while the engine runs, then resets."""
    coordinator, vehicle = await _setup_entry(hass, options={CONF_DRIVING_INTERVAL: 90})

    vehicle.engine_state = "engine_running"
    coordinator._update_activity_intervals()
    assert coordinator._update_intervals["driving"] == timedelta(seconds=90)

    vehicle.engine_state = "engine_off"
    coordinator._update_activity_intervals()
    assert "driving" not in coordinator._update_intervals


@pytest.mark.asyncio()
async def test_rendering_sensors_does_not_request_refresh(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """Writing sensor states while charging/driving must not trigger refreshes."""
    coordinator, vehicle = await _setup_entry(hass)
    vehicle.battery.charging_current = ValueWithUnit(16.0, "A")
    vehicle.engine_state = "engine_running"

    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_update_listeners()
    await hass.async_block_till_done()

    coordinator.async_request_refresh.assert_not_awaited()


@pytest.mark.asyncio()
async def test_scan_interval_option_applies_from_start(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """The configured scan interval is used without waiting for a reset."""
    coordinator, _ = await _setup_entry(hass, options={"scan_interval": 600})
    assert coordinator.update_interval == timedelta(seconds=600)
