"""Unit tests for the horn and light buttons."""

import json
from unittest.mock import AsyncMock, patch

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


def _find_button(hass: HomeAssistant, name: str) -> str | None:
    for entity_id in hass.states.async_entity_ids("button"):
        if entity_id.startswith("button.smart") and name in entity_id:
            return entity_id
    return None


def _telematics_payloads(router: respx.Router) -> list[dict]:
    return [
        json.loads(call.request.content)
        for call in router.calls
        if call.request.method == "PUT"
        and "/vehicle/telematics/" in call.request.url.path
    ]


async def _press(hass: HomeAssistant, entity_id: str) -> None:
    await hass.services.async_call(
        "button", "press", {"entity_id": entity_id}, blocking=True
    )
    await hass.async_block_till_done()


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    ("name", "action"), [("flash_lights", "light-flash"), ("honk_horn", "horn")]
)
async def test_button_sends_rhl_command(
    hass: HomeAssistant, smart_fixture: respx.Router, name: str, action: str
):
    """Test that pressing a button sends the matching RHL command."""
    await _setup_entry(hass)
    entity_id = _find_button(hass, name)
    assert entity_id is not None, f"{name} button not found"

    await _press(hass, entity_id)

    payload = _telematics_payloads(smart_fixture)[-1]
    assert payload["serviceId"] == "RHL"
    assert payload["serviceParameters"] == [{"key": "rhl", "value": action}]


@pytest.mark.asyncio()
async def test_rejected_command_raises(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """Test that a command the vehicle does not accept surfaces an error."""
    await _setup_entry(hass)
    entity_id = _find_button(hass, "honk_horn")

    with (
        patch(
            "pysmarthashtag.control.horn_light.HornLightControl.honk_horn",
            new=AsyncMock(return_value=False),
        ),
        pytest.raises(HomeAssistantError),
    ):
        await _press(hass, entity_id)
