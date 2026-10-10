"""Unit tests for the integration services."""

import json
from unittest.mock import AsyncMock, patch

import pytest
import respx
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smarthashtag.const import DOMAIN


async def _setup_entry(hass: HomeAssistant) -> str:
    """Set up the integration and return the device id of the vehicle."""
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
    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert len(devices) == 1
    return devices[0].id


def _data(device_id: str, **overrides) -> dict:
    return {
        "device_id": device_id,
        "latitude": 52.5163,
        "longitude": 13.3777,
        "name": "Brandenburger Tor",
        "address": "Pariser Platz, 10117 Berlin",
        **overrides,
    }


@pytest.mark.asyncio()
async def test_send_destination_posts_to_vehicle(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """Test that the destination is sent to the selected vehicle."""
    device_id = await _setup_entry(hass)
    route = smart_fixture.post(url__regex=r".*/ihu/send/to/car.*").respond(
        200, json={"code": "1000", "success": True}
    )

    await hass.services.async_call(
        DOMAIN, "send_destination", _data(device_id), blocking=True
    )

    assert route.called
    request = route.calls.last.request
    assert "vin=TestVIN0000000001" in str(request.url)
    assert json.loads(request.content) == {
        "lat": 52.5163,
        "lon": 13.3777,
        "name": "Brandenburger Tor",
        "address": "Pariser Platz, 10117 Berlin",
    }


@pytest.mark.asyncio()
async def test_send_destination_rejected_raises(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """Test that a destination the vehicle does not accept surfaces an error."""
    device_id = await _setup_entry(hass)

    with (
        patch(
            "pysmarthashtag.account.SmartAccount.send_destination_to_car",
            new=AsyncMock(return_value=False),
        ),
        pytest.raises(HomeAssistantError),
    ):
        await hass.services.async_call(
            DOMAIN, "send_destination", _data(device_id), blocking=True
        )


@pytest.mark.asyncio()
async def test_send_destination_unknown_device_raises(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """Test that a device of another integration is refused."""
    await _setup_entry(hass)

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "send_destination", _data("does-not-exist"), blocking=True
        )


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    "overrides",
    [{"latitude": 91}, {"longitude": -181}, {"name": ""}],
)
async def test_send_destination_validates_input(
    hass: HomeAssistant, smart_fixture: respx.Router, overrides: dict
):
    """Test that invalid coordinates and names are rejected."""
    device_id = await _setup_entry(hass)

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN, "send_destination", _data(device_id, **overrides), blocking=True
        )
