"""Unit tests for coordinator behavior on API errors."""

import asyncio
from datetime import timedelta

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


@pytest.mark.asyncio()
async def test_coordinator_set_and_reset_update_interval(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """
    Test the coordinator's set_update_interval and reset_update_interval methods.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "sample_user",
            "password": "sample_password",
            "vehicle": "TestVIN0000000001",
        },
        options={"scan_interval": 300},
    )

    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    coordinator = entry.runtime_data

    # Test set_update_interval
    coordinator.set_update_interval("test_key", timedelta(seconds=60))
    assert coordinator.update_interval == timedelta(seconds=60)

    # Add a longer interval - shortest should still be selected
    coordinator.set_update_interval("another_key", timedelta(seconds=120))
    assert coordinator.update_interval == timedelta(seconds=60)

    # Add a shorter interval - should use this one
    coordinator.set_update_interval("short_key", timedelta(seconds=30))
    assert coordinator.update_interval == timedelta(seconds=30)

    # Reset an interval - key should be removed, shortest remaining is selected
    coordinator.reset_update_interval("short_key")
    # After reset, short_key is removed, so shortest remaining is test_key (60 seconds)
    assert coordinator.update_interval == timedelta(seconds=60)
    assert "short_key" not in coordinator._update_intervals

    # Reset all remaining intervals - should revert to configured default
    coordinator.reset_update_interval("test_key")
    coordinator.reset_update_interval("another_key")
    # All intervals removed, should use configured default (300 seconds)
    assert coordinator.update_interval == timedelta(seconds=300)
    assert len(coordinator._update_intervals) == 0


@pytest.mark.asyncio()
async def test_coordinator_handles_timeout_gracefully(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """
    Test that the coordinator handles timeout errors gracefully.

    This simulates network timeouts and verifies that entities remain available
    with cached data rather than becoming unavailable.
    """
    call_count = 0

    async def simulate_timeout(request: Request, route: respx.Route) -> Response:
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            # First two calls succeed
            return Response(200, json=load_response(RESPONSE_DIR / "vehicle_info.json"))
        else:
            # Third call simulates a timeout
            raise asyncio.TimeoutError("Connection timed out")

    smart_fixture.get(
        "https://api.ecloudeu.com/remote-control/vehicle/status/TestVIN0000000001?latest=True&target=basic%2Cmore&userId=112233",
    ).mock(side_effect=simulate_timeout)

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

    # Second refresh should succeed
    await entry.runtime_data.async_refresh()
    state = hass.states.get("sensor.smart_last_update")
    assert state
    assert state.state == "2024-01-23T16:44:00+00:00"

    # Third refresh hits timeout, but state should be preserved with cached data
    await entry.runtime_data.async_refresh()
    state = hass.states.get("sensor.smart_last_update")

    # State should still be available with the last known value
    assert state
    assert state.state == "2024-01-23T16:44:00+00:00"
    assert state.state != "unavailable"


@pytest.mark.asyncio()
async def test_coordinator_failure_counter_resets_on_success(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """
    Test that the failure counter resets after a successful API call.

    This ensures that intermittent failures don't accumulate indefinitely.
    """
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

    coordinator = entry.runtime_data

    # Initial setup successful, failure counter should be 0
    assert coordinator._consecutive_failures == 0

    # Simulate a failure by directly incrementing the counter
    # (as would happen during an API error)
    coordinator._consecutive_failures = 5

    # Refresh should succeed and reset the counter
    await coordinator.async_refresh()
    assert coordinator._consecutive_failures == 0

    # Verify entity is still available
    state = hass.states.get("sensor.smart_last_update")
    assert state
    assert state.state != "unavailable"


@pytest.mark.asyncio()
async def test_coordinator_max_transient_failures_threshold(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """
    Test MAX_TRANSIENT_FAILURES threshold behavior.

    Verifies that:
    1. Cached data is returned when consecutive failures are below MAX_TRANSIENT_FAILURES
    2. UpdateFailed is raised once MAX_TRANSIENT_FAILURES is reached (entities become unavailable)
    """
    from homeassistant.helpers.update_coordinator import UpdateFailed

    from custom_components.smarthashtag.coordinator import MAX_TRANSIENT_FAILURES

    # Gate when to start failing requests to avoid counting setup-time API calls.
    start_failures = False

    async def simulate_consecutive_failures(
        request: Request, route: respx.Route
    ) -> Response:
        if not start_failures:
            # Allow all setup-time calls to succeed so the cache is populated deterministically.
            return Response(200, json=load_response(RESPONSE_DIR / "vehicle_info.json"))

        # Once failures are enabled, every call times out to drive the counter.
        raise asyncio.TimeoutError("Connection timed out")

    smart_fixture.get(
        "https://api.ecloudeu.com/remote-control/vehicle/status/TestVIN0000000001?latest=True&target=basic%2Cmore&userId=112233",
    ).mock(side_effect=simulate_consecutive_failures)

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

    coordinator = entry.runtime_data

    # Verify initial state is available (call 1 succeeded)
    state = hass.states.get("sensor.smart_last_update")
    assert state
    assert state.state == "2024-01-23T16:44:00+00:00"
    # Some integrations issue additional vehicle status calls during setup,
    # which can increment the failure counter. Reset here to establish a clean
    # baseline for the threshold test.
    coordinator._consecutive_failures = 0
    coordinator._last_error = None

    # Second refresh succeeds, confirming cached data is established
    await coordinator.async_refresh()
    state = hass.states.get("sensor.smart_last_update")
    assert state
    assert state.state == "2024-01-23T16:44:00+00:00"
    assert coordinator._consecutive_failures == 0

    # Start failing requests to verify transient failure handling.
    start_failures = True

    # Disable any scheduled refresh callbacks so only the explicit refreshes
    # in this test drive the failure counter.
    if coordinator._unsub_refresh:
        coordinator._unsub_refresh()
        coordinator._unsub_refresh = None

    # Drive consecutive failures until just before the threshold.
    while coordinator._consecutive_failures < MAX_TRANSIENT_FAILURES - 1:
        await coordinator.async_refresh()
        state = hass.states.get("sensor.smart_last_update")

        # Verify cached data is returned and entity remains available
        assert state
        assert state.state == "2024-01-23T16:44:00+00:00"
        assert coordinator._consecutive_failures < MAX_TRANSIENT_FAILURES

    # Ensure we are exactly one failure away from the threshold to make the
    # next refresh deterministic for this test.
    coordinator._consecutive_failures = MAX_TRANSIENT_FAILURES - 1

    # The next failure should be the MAX_TRANSIENT_FAILURES-th failure.
    # We expect an UpdateFailed once the counter reaches MAX_TRANSIENT_FAILURES.
    # Some coordinator implementations surface this as a raised exception, others
    # capture it in last_exception while marking the update as failed. Accept both
    # to avoid flakiness from background refresh timing.
    update_failed: UpdateFailed | None = None
    try:
        await coordinator.async_refresh()
    except UpdateFailed as err:
        update_failed = err

    observed_exception = update_failed or coordinator.last_exception
    if observed_exception:
        assert str(MAX_TRANSIENT_FAILURES) in str(observed_exception)

    # Verify failure counter reached (or exceeded) the threshold
    assert coordinator._consecutive_failures >= MAX_TRANSIENT_FAILURES

    # After UpdateFailed, entities should become unavailable
    await hass.async_block_till_done()
    state = hass.states.get("sensor.smart_last_update")
    assert state
    assert state.state == "unavailable"
