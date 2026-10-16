"""Tests for the Smart #5 single seat heating switches."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from pysmarthashtag.control.climate import HeatingLocation, RearHeatingLocation

from custom_components.smarthashtag.const import DEFAULT_SEATHEATING_LEVEL
from custom_components.smarthashtag.switch import (
    SINGLE_SEAT_SWITCH_DESCRIPTIONS,
    SmartHeatingSwitch,
    async_setup_entry,
)

TRANSLATIONS = Path(__file__).parents[1] / "custom_components/smarthashtag/translations"
VIN = "TestVIN0000000001"


def _switch(description, selects=None, climate_control=None) -> SmartHeatingSwitch:
    coordinator = MagicMock()
    coordinator.config_entry.entry_id = "entry"
    coordinator.config_entry.data = {"selects": selects or {}}
    coordinator.account.vehicles = {
        VIN: MagicMock(climate_control=climate_control or MagicMock())
    }
    return SmartHeatingSwitch(coordinator, VIN, description)


def test_one_switch_per_seat_disabled_by_default():
    """There are four switches, one seat each, all hidden by default."""
    locations = [d.locations for d in SINGLE_SEAT_SWITCH_DESCRIPTIONS]
    assert locations == [
        (HeatingLocation.DRIVER_SEAT,),
        (HeatingLocation.PASSENGER_SEAT,),
        (RearHeatingLocation.REAR_LEFT,),
        (RearHeatingLocation.REAR_RIGHT,),
    ]
    for description in SINGLE_SEAT_SWITCH_DESCRIPTIONS:
        assert description.enabled_default is False
        assert _switch(description).entity_registry_enabled_default is False


@pytest.mark.parametrize("language", ["en", "de"])
def test_single_seat_switches_are_translated(language):
    translations = json.loads((TRANSLATIONS / f"{language}.json").read_text())
    for description in SINGLE_SEAT_SWITCH_DESCRIPTIONS:
        assert f"{description.key}_control" in translations["entity"]["switch"]


@pytest.mark.asyncio
async def test_front_seat_is_sent_alone_with_selected_level():
    climate_control = MagicMock()
    climate_control.set_heating = AsyncMock(return_value=True)
    climate_control.set_rear_heating = AsyncMock(return_value=True)
    switch = _switch(
        SINGLE_SEAT_SWITCH_DESCRIPTIONS[1],
        selects={HeatingLocation.PASSENGER_SEAT.value: 2},
        climate_control=climate_control,
    )
    assert await switch._send_command(True) is True
    climate_control.set_heating.assert_awaited_once_with(
        True, {HeatingLocation.PASSENGER_SEAT: 2}
    )
    climate_control.set_rear_heating.assert_not_awaited()


@pytest.mark.asyncio
async def test_rear_seat_uses_rear_heating_and_default_level_and_stops():
    climate_control = MagicMock()
    climate_control.set_heating = AsyncMock(return_value=True)
    climate_control.set_rear_heating = AsyncMock(return_value=True)
    switch = _switch(
        SINGLE_SEAT_SWITCH_DESCRIPTIONS[2], climate_control=climate_control
    )
    assert await switch._send_command(True) is True
    climate_control.set_rear_heating.assert_awaited_once_with(
        True, {RearHeatingLocation.REAR_LEFT: DEFAULT_SEATHEATING_LEVEL}
    )
    assert await switch._send_command(False) is True
    climate_control.set_rear_heating.assert_awaited_with(
        False, {RearHeatingLocation.REAR_LEFT: 0}
    )
    climate_control.set_heating.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("use_zaf", "has_rear", "expected"),
    [(True, True, 4), (False, True, 0), (True, False, 0)],
)
async def test_single_seat_switches_only_on_smart5(use_zaf, has_rear, expected):
    """The switches are only added for a #5 with a pysmarthashtag that can do it."""
    climate_control = MagicMock(spec=["use_zaf", "set_heating", "set_defrost"])
    climate_control.use_zaf = use_zaf
    if has_rear:
        climate_control.set_rear_heating = AsyncMock()
    vehicle = MagicMock(climate_control=climate_control, window_control=None)
    coordinator = MagicMock()
    coordinator.config_entry.data = {"vehicle": VIN}
    coordinator.config_entry.entry_id = "entry"
    coordinator.account.vehicles = {VIN: vehicle}
    entry = MagicMock(runtime_data=coordinator)
    added = []
    await async_setup_entry(MagicMock(), entry, lambda e, **kw: added.extend(e))
    keys = [
        e._description.key
        for e in added
        if isinstance(e, SmartHeatingSwitch)
        and e._description in SINGLE_SEAT_SWITCH_DESCRIPTIONS
    ]
    assert len(keys) == expected
