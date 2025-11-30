"""Unit tests for coordinator behavior on API errors."""

import pytest
import respx
from homeassistant.core import HomeAssistant
from httpx import Request, Response
from pysmarthashtag.tests import RESPONSE_DIR, load_response
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smarthashtag.const import DOMAIN


@pytest.mark.asyncio()
async def test_coordinator_returns_last_data_on_api_error(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """
    Test that the coordinator returns last known data when API returns an error.

    This simulates the case where the API returns an error (e.g., 1509: Service maintenance)
    and verifies that the sensor values are preserved instead of becoming unavailable.
    """
    call_count = 0

    async def simulate_api_error(request: Request, route: respx.Route) -> Response:
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            # First two calls succeed (initial setup + first refresh)
            return Response(200, json=load_response(RESPONSE_DIR / "vehicle_info.json"))
        else:
            # Third call returns API error (simulating maintenance)
            return Response(
                200,  # HTTP 200 but with error code in JSON body
                json={
                    "code": "1509",
                    "message": "Service maintenance, try again later.",
                },
            )

    smart_fixture.get(
        "https://api.ecloudeu.com/remote-control/vehicle/status/TestVIN0000000001?latest=True&target=basic%2Cmore&userId=112233",
    ).mock(side_effect=simulate_api_error)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "sample_user",
            "password": "sample_password",
            "vehicle": "TestVIN0000000001",
        },
    )

    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Verify initial state is available
    state = hass.states.get("sensor.smart_last_update")
    assert state
    assert state.state == "2024-01-23T16:44:00+00:00"

    # Refresh should succeed (second call)
    await entry.runtime_data.async_refresh()
    state = hass.states.get("sensor.smart_last_update")
    assert state
    assert state.state == "2024-01-23T16:44:00+00:00"

    # Third refresh should hit API error, but state should be preserved
    await entry.runtime_data.async_refresh()
    state = hass.states.get("sensor.smart_last_update")

    # State should still be available with the last known value
    assert state
    assert state.state == "2024-01-23T16:44:00+00:00"
    # The entity should not become unavailable
    assert state.state != "unavailable"
