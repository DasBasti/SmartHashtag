"""Unit tests for the charging lid switch (Smart #5 only)."""

import json

import pytest
import respx
from homeassistant.core import HomeAssistant
from pysmarthashtag.const import API_BASE_URL_V2
from pysmarthashtag.tests import RESPONSE_DIR, load_response
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smarthashtag.const import DOMAIN

SMART_1_VIN = "TestVIN0000000001"
SMART_5_VIN = "TestVIN0000000002"


async def _setup_entry(hass: HomeAssistant, vin: str) -> None:
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


@pytest.mark.asyncio()
async def test_no_charging_lid_switch_without_motorised_lid(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """Test that a Smart #1 gets no charging lid switch."""
    await _setup_entry(hass, SMART_1_VIN)

    assert _find_switch(hass, "charging_lid") is None


@pytest.mark.asyncio()
async def test_charging_lid_switch_follows_reported_state(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """Test that the Smart #5 charging lid switch reflects the reported lid state."""
    await _setup_entry(hass, SMART_5_VIN)

    entity_id = _find_switch(hass, "charging_lid")
    assert entity_id is not None, "Charging lid switch entity not found"
    # The #5 fixture reports "chargeLidDcAcStatus": "1"
    assert hass.states.get(entity_id).state == "on"


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    ("service", "service_id", "expected_state"),
    [("turn_on", "RDO", "on"), ("turn_off", "RDC", "off")],
)
async def test_charging_lid_switch_sends_command(
    hass: HomeAssistant,
    smart_fixture: respx.Router,
    service: str,
    service_id: str,
    expected_state: str,
):
    """Test that the switch sends the charging lid open or close command."""
    smart_fixture.put(
        API_BASE_URL_V2 + "/remote-control/vehicle/telematics/" + SMART_5_VIN
    ).respond(200, json=load_response(RESPONSE_DIR / "climate_success.json"))
    await _setup_entry(hass, SMART_5_VIN)
    entity_id = _find_switch(hass, "charging_lid")

    await hass.services.async_call(
        "switch", service, {"entity_id": entity_id}, blocking=True
    )
    await hass.async_block_till_done()

    payload = _telematics_payloads(smart_fixture)[-1]
    assert payload["serviceId"] == service_id
    assert payload["serviceParameters"] == [
        {"key": "target", "value": "front-charge-lid"}
    ]
    assert hass.states.get(entity_id).state == expected_state
