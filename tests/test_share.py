"""Unit tests for resolving shared maps links."""

from unittest.mock import AsyncMock, patch

import pytest
import respx
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smarthashtag.const import DOMAIN
from custom_components.smarthashtag.share import (
    SharedLocation,
    SharedLocationError,
    async_resolve_shared_location,
    extract_url,
    parse_maps_url,
)

DIR_URL = (
    "https://www.google.com/maps/dir/49.6464495,8.573442/Back-+und+Brauhaus+Dray%C3%9F/"
    "data=!4m12!4m11!1m1!4e1!1m5!1m4!1s0x410cae1a60b14e47:0x207587fcbb84e0dd"
    "!8m2!3d49.654263199999995!4d8.5675885!2m1!11b1!3e0?utm_source=mstt_0&skid=1"
)


def test_parse_directions_url():
    """The destination of a shared route is taken, not its origin."""
    assert parse_maps_url(DIR_URL) == SharedLocation(
        49.654263199999995, 8.5675885, "Back- und Brauhaus Drayß"
    )


def test_parse_place_url():
    """A shared place uses the name and the coordinates in the path."""
    url = "https://www.google.com/maps/place/Brandenburger+Tor/@52.5162746,13.3777041,17z/data=!3m1"
    assert parse_maps_url(url) == SharedLocation(
        52.5162746, 13.3777041, "Brandenburger Tor"
    )


def test_parse_plain_coordinate_destination():
    """A destination given as coordinates is named after them."""
    url = "https://www.google.com/maps/dir/49.1,8.1/50.25,9.5/"
    assert parse_maps_url(url) == SharedLocation(50.25, 9.5, "50.25000, 9.50000")


def test_parse_without_coordinates_raises():
    with pytest.raises(SharedLocationError):
        parse_maps_url("https://www.google.com/maps/search/pizza")


def test_extract_url_from_text():
    assert (
        extract_url("Look at this https://maps.app.goo.gl/abc123 nice")
        == "https://maps.app.goo.gl/abc123"
    )
    with pytest.raises(SharedLocationError):
        extract_url("no link here")


class _FakeResponse:
    def __init__(self, url: str) -> None:
        self.url = url

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class _FakeSession:
    def __init__(self, final_url: str) -> None:
        self.final_url = final_url
        self.requested: list[str] = []

    def get(self, url, **kwargs):
        self.requested.append(url)
        return _FakeResponse(self.final_url)


@pytest.mark.asyncio()
async def test_resolve_follows_short_link():
    session = _FakeSession(DIR_URL)
    location = await async_resolve_shared_location(
        session, "https://maps.app.goo.gl/W9bykxJhd8GsNXvUA"
    )
    assert session.requested == ["https://maps.app.goo.gl/W9bykxJhd8GsNXvUA"]
    assert location.latitude == pytest.approx(49.6542632)


@pytest.mark.asyncio()
async def test_resolve_refuses_foreign_hosts():
    """Links to other sites are never requested."""
    session = _FakeSession(DIR_URL)
    with pytest.raises(SharedLocationError):
        await async_resolve_shared_location(session, "http://192.168.1.1/admin")
    assert session.requested == []


@pytest.mark.asyncio()
async def test_resolve_refuses_redirect_to_foreign_host():
    session = _FakeSession("https://example.com/maps/dir/1,2/x/")
    with pytest.raises(SharedLocationError):
        await async_resolve_shared_location(
            session, "https://maps.app.goo.gl/W9bykxJhd8GsNXvUA"
        )


async def _setup_entry(hass: HomeAssistant) -> str:
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
    return devices[0].id


@pytest.mark.asyncio()
async def test_send_shared_destination_sends_resolved_location(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    device_id = await _setup_entry(hass)
    send = AsyncMock(return_value=True)

    with (
        patch(
            "custom_components.smarthashtag.services.async_resolve_shared_location",
            new=AsyncMock(return_value=SharedLocation(49.65, 8.56, "Brauhaus")),
        ),
        patch("pysmarthashtag.account.SmartAccount.send_destination_to_car", new=send),
    ):
        await hass.services.async_call(
            DOMAIN,
            "send_shared_destination",
            {"device_id": device_id, "url": "https://maps.app.goo.gl/x"},
            blocking=True,
        )

    send.assert_awaited_once_with("TestVIN0000000001", 49.65, 8.56, "Brauhaus", "")


@pytest.mark.asyncio()
async def test_send_shared_destination_unresolvable_raises(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    device_id = await _setup_entry(hass)

    with (
        patch(
            "custom_components.smarthashtag.services.async_resolve_shared_location",
            new=AsyncMock(side_effect=SharedLocationError("no link found")),
        ),
        pytest.raises(ServiceValidationError),
    ):
        await hass.services.async_call(
            DOMAIN,
            "send_shared_destination",
            {"device_id": device_id, "url": "nothing"},
            blocking=True,
        )


@pytest.mark.asyncio()
async def test_send_shared_destination_rejected_raises(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    device_id = await _setup_entry(hass)

    with (
        patch(
            "custom_components.smarthashtag.services.async_resolve_shared_location",
            new=AsyncMock(return_value=SharedLocation(49.65, 8.56, "Brauhaus")),
        ),
        patch(
            "pysmarthashtag.account.SmartAccount.send_destination_to_car",
            new=AsyncMock(return_value=False),
        ),
        pytest.raises(HomeAssistantError),
    ):
        await hass.services.async_call(
            DOMAIN,
            "send_shared_destination",
            {"device_id": device_id, "url": "https://maps.app.goo.gl/x"},
            blocking=True,
        )
