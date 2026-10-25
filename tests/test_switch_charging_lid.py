"""Unit tests for the charging flap switch (Smart #5 only)."""

import json
from unittest.mock import patch

import pytest
import respx
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smarthashtag.const import DOMAIN


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


def _find_switch(hass: HomeAssistant) -> str | None:
    for entity_id in hass.states.async_entity_ids("switch"):
        if entity_id.startswith("switch.smart") and "charging_flap" in entity_id:
            return entity_id
    return None


def _telematics_payloads(router: respx.Router) -> list[dict]:
    return [
        json.loads(call.request.content)
        for call in router.calls
        if call.request.method == "PUT"
        and "/vehicle/telematics/" in call.request.url.path
    ]


@pytest.fixture
def smart_5():
    """Make the fixture vehicle (series HX11) count as a Smart #5."""
    with patch("pysmarthashtag.vehicle.vehicle.SERIES_CODE_PREFIX_SMART_5", "HX"):
        yield


@pytest.mark.asyncio()
async def test_no_charging_flap_switch_on_other_models(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """Models without a motorised charging flap get no switch."""
    await _setup_entry(hass)
    assert _find_switch(hass) is None


@pytest.mark.asyncio()
async def test_charging_flap_switch_follows_reported_state(
    hass: HomeAssistant, smart_fixture: respx.Router, smart_5
):
    """The fixture reports a closed flap."""
    await _setup_entry(hass)
    entity_id = _find_switch(hass)
    assert entity_id is not None, "Charging flap switch entity not found"
    assert hass.states.get(entity_id).state == "off"


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    ("service", "service_id"), [("turn_on", "RDO"), ("turn_off", "RDC")]
)
async def test_charging_flap_switch_sends_command(
    hass: HomeAssistant,
    smart_fixture: respx.Router,
    smart_5,
    service: str,
    service_id: str,
):
    """Turning the switch on or off sends the RDO or RDC service."""
    await _setup_entry(hass)
    entity_id = _find_switch(hass)
    assert entity_id is not None

    await hass.services.async_call(
        "switch", service, {"entity_id": entity_id}, blocking=True
    )
    await hass.async_block_till_done()

    assert _telematics_payloads(smart_fixture)[-1]["serviceId"] == service_id
    expected = "on" if service == "turn_on" else "off"
    assert hass.states.get(entity_id).state == expected


@pytest.mark.asyncio()
async def test_charging_flap_switch_rejected_command_raises(
    hass: HomeAssistant, smart_fixture: respx.Router, smart_5
):
    """A command the vehicle does not accept raises an error."""
    await _setup_entry(hass)
    entity_id = _find_switch(hass)
    vehicle = hass.config_entries.async_entries(DOMAIN)[
        0
    ].runtime_data.account.vehicles["TestVIN0000000001"]
    with (
        patch.object(vehicle.charging_lid_control, "open", return_value=False),
        pytest.raises(HomeAssistantError),
    ):
        await hass.services.async_call(
            "switch", "turn_on", {"entity_id": entity_id}, blocking=True
        )
