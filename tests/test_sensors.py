"""Unit tests for _handle_error function."""

import pytest
import respx
from homeassistant.core import HomeAssistant
from httpx import Request, Response
from pysmarthashtag.tests import RESPONSE_DIR, load_response
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smarthashtag.const import DOMAIN
from custom_components.smarthashtag.sensor import remove_vin_from_key, vin_from_key


def test_remove_vin_from_key():
    """Test the remove_vin_from_key function.

    This function calls the remove_vin_from_key function with a sample key and checks that it returns the key with the VIN removed.
    """
    # Define the sample key
    key = "vin1234567890_odometer"

    # Call the function
    new_key = remove_vin_from_key(key)

    # Check that the returned key is correct
    assert new_key == "odometer"


def test_vin_from_key():
    """Test the vin_from_key function.

    This function calls the vin_from_key function with a sample key and checks that it returns the VIN from the key.
    """
    # Define the sample key
    key = "TestVIN0000000001_odometer"

    # Call the function
    vin = vin_from_key(key)

    # Check that the returned VIN is correct
    assert vin == "TestVIN0000000001"


@pytest.mark.asyncio()
async def test_sensor_updates(hass: HomeAssistant, smart_fixture: respx.Router):
    """
    Test the sensors function

    This loads a sample testing configuration from the pysmarthashtag package and checks that the sensors are updated correctly.
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
    await entry.runtime_data.async_refresh()

    state = hass.states.get("sensor.smart_last_update")

    assert state
    assert state.state == "2024-01-23T16:44:00+00:00"


@pytest.mark.asyncio()
async def test_odometer_updates(hass: HomeAssistant, smart_fixture: respx.Router):
    """
    Test the odometer function

    This loads sample data from pysmarthashtag but increases odometer value each call.
    """

    async def increase_odometer(request: Request, route: respx.Route) -> Response:
        response = load_response(RESPONSE_DIR / "vehicle_info.json")
        response["data"]["vehicleStatus"]["additionalVehicleStatus"][
            "maintenanceStatus"
        ]["odometer"] = str(
            route.call_count
            + float(
                response["data"]["vehicleStatus"]["additionalVehicleStatus"][
                    "maintenanceStatus"
                ]["odometer"]
            )
        )
        return Response(200, json=response)

    smart_fixture.get(
        "https://api.ecloudeu.com/remote-control/vehicle/status/TestVIN0000000001?latest=True&target=basic%2Cmore&userId=112233",
    ).mock(side_effect=increase_odometer)

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

    state = hass.states.get("sensor.smart_odometer")

    assert state
    assert state.state == "502"

    await entry.runtime_data.async_refresh()

    state = hass.states.get("sensor.smart_odometer")

    assert state
    assert state.state == "503"


@pytest.mark.asyncio()
async def test_battery_updates(hass: HomeAssistant, smart_fixture: respx.Router):
    """
    Test the odometer function

    This loads sample data from pysmarthashtag but increases odometer value each call.
    """

    async def deplete_battery(request: Request, route: respx.Route) -> Response:
        response = load_response(RESPONSE_DIR / "vehicle_info.json")
        response["data"]["vehicleStatus"]["additionalVehicleStatus"][
            "electricVehicleStatus"
        ]["chargeLevel"] = str(
            int(
                response["data"]["vehicleStatus"]["additionalVehicleStatus"][
                    "electricVehicleStatus"
                ]["chargeLevel"]
            )
            - route.call_count
        )
        return Response(200, json=response)

    smart_fixture.get(
        "https://api.ecloudeu.com/remote-control/vehicle/status/TestVIN0000000001?latest=True&target=basic%2Cmore&userId=112233",
    ).mock(side_effect=deplete_battery)

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

    state = hass.states.get("sensor.smart_battery")

    assert state
    assert state.state == "45"

    await entry.runtime_data.async_refresh()

    state = hass.states.get("sensor.smart_battery")

    assert state
    assert state.state == "44"


@pytest.mark.asyncio()
async def test_charging_ac_power_updates(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """
    Test the charging power calculation function

    This loads sample data from pysmarthashtag but changed charging values.

    Tests AC charging with various voltage/current combinations:
    - Zero power (0V, 0A)
    - Standard charging (230V, 2A and 3A)
    - 3-phase high-power charging (400V, 16A)
    """
    value_target = (0, 0)

    async def simulate_ac_charging(request: Request, route: respx.Route) -> Response:
        response = load_response(RESPONSE_DIR / "vehicle_info.json")
        # pysmarthashtag ChargingState['CHARGING']
        response["data"]["vehicleStatus"]["additionalVehicleStatus"][
            "electricVehicleStatus"
        ]["chargerState"] = "2"
        response["data"]["vehicleStatus"]["additionalVehicleStatus"][
            "electricVehicleStatus"
        ]["chargeUAct"] = str(float(value_target[0]))
        response["data"]["vehicleStatus"]["additionalVehicleStatus"][
            "electricVehicleStatus"
        ]["chargeIAct"] = str(float(value_target[1]))

        return Response(200, json=response)

    smart_fixture.get(
        "https://api.ecloudeu.com/remote-control/vehicle/status/TestVIN0000000001?latest=True&target=basic%2Cmore&userId=112233",
    ).mock(side_effect=simulate_ac_charging)

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

    state = hass.states.get("sensor.smart_charging_status")
    assert state
    assert state.state == "charging"

    state = hass.states.get("sensor.smart_charging_power")
    assert state
    assert state.state == "0.0"

    value_target = (230, 2)
    await entry.runtime_data.async_refresh()

    state = hass.states.get("sensor.smart_charging_power")
    assert state
    assert state.state == "460.0"

    value_target = (230, 3)
    await entry.runtime_data.async_refresh()

    state = hass.states.get("sensor.smart_charging_power")
    assert state
    assert state.state == "690.0"

    # test 3-phase 11kW (11085.1251684408W)
    value_target = (400, 16)
    await entry.runtime_data.async_refresh()

    state = hass.states.get("sensor.smart_charging_power")
    assert state
    assert state.state == "11085.1251684408"


@pytest.mark.asyncio()
async def test_charging_dc_power_updates(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """
    Test the charging power calculation function

    This loads sample data from pysmarthashtag but changed charging.

    Tests DC charging with different current values (0A, 100A, 150A)
    to verify correct power calculation at 417V DC voltage.
    """
    value_target = 0

    async def simulate_dc_charging(request: Request, route: respx.Route) -> Response:
        response = load_response(RESPONSE_DIR / "vehicle_info.json")
        # pysmarthashtag ChargingState['CHARGING']
        response["data"]["vehicleStatus"]["additionalVehicleStatus"][
            "electricVehicleStatus"
        ]["chargerState"] = "15"
        response["data"]["vehicleStatus"]["additionalVehicleStatus"][
            "electricVehicleStatus"
        ]["dcChargeIAct"] = str(float(value_target))

        return Response(200, json=response)

    smart_fixture.get(
        "https://api.ecloudeu.com/remote-control/vehicle/status/TestVIN0000000001?latest=True&target=basic%2Cmore&userId=112233",
    ).mock(side_effect=simulate_dc_charging)

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

    state = hass.states.get("sensor.smart_charging_status")
    assert state
    assert state.state == "dc_charging"

    state = hass.states.get("sensor.smart_charging_power")
    assert state
    assert state.state == "0.0"

    value_target = 100
    await entry.runtime_data.async_refresh()

    state = hass.states.get("sensor.smart_charging_power")
    assert state
    assert state.state == "41700"

    value_target = 150
    await entry.runtime_data.async_refresh()

    state = hass.states.get("sensor.smart_charging_power")
    assert state
    assert state.state == "62550"


@pytest.mark.asyncio()
async def test_charging_power_retains_value_during_charging(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """
    Test that charging power retains last valid value when API returns 0 during active charging.

    This test simulates the scenario where:
    1. Car starts charging with 0W (as per initial API response)
    2. Then receives valid power reading (460W)
    3. API temporarily returns 0W while charging status is still "CHARGING"
    4. The sensor should retain the last valid value (460W) instead of jumping to 0W

    This addresses issue #292: Charging power sometimes stays at 0W during charging.
    """
    # Start with 0 values (default), then switch to valid values, then back to 0
    value_target = (0, 0)
    return_zero = False

    async def simulate_intermittent_charging(
        request: Request, route: respx.Route
    ) -> Response:
        nonlocal value_target, return_zero
        response = load_response(RESPONSE_DIR / "vehicle_info.json")
        # pysmarthashtag ChargingState['CHARGING']
        response["data"]["vehicleStatus"]["additionalVehicleStatus"][
            "electricVehicleStatus"
        ]["chargerState"] = "2"

        if return_zero:
            # Simulate API returning 0 values while still charging
            response["data"]["vehicleStatus"]["additionalVehicleStatus"][
                "electricVehicleStatus"
            ]["chargeUAct"] = "0.0"
            response["data"]["vehicleStatus"]["additionalVehicleStatus"][
                "electricVehicleStatus"
            ]["chargeIAct"] = "0.0"
        else:
            response["data"]["vehicleStatus"]["additionalVehicleStatus"][
                "electricVehicleStatus"
            ]["chargeUAct"] = str(float(value_target[0]))
            response["data"]["vehicleStatus"]["additionalVehicleStatus"][
                "electricVehicleStatus"
            ]["chargeIAct"] = str(float(value_target[1]))

        return Response(200, json=response)

    smart_fixture.get(
        "https://api.ecloudeu.com/remote-control/vehicle/status/TestVIN0000000001?latest=True&target=basic%2Cmore&userId=112233",
    ).mock(side_effect=simulate_intermittent_charging)

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

    # Verify initial charging state (starting with 0W)
    state = hass.states.get("sensor.smart_charging_status")
    assert state
    assert state.state == "charging"

    state = hass.states.get("sensor.smart_charging_power")
    assert state
    assert state.state == "0.0"

    # Now set valid charging power
    value_target = (230, 2)  # 460W
    await entry.runtime_data.async_refresh()

    state = hass.states.get("sensor.smart_charging_power")
    assert state
    assert state.state == "460.0"

    # Now simulate API returning 0 while still in charging state
    return_zero = True
    await entry.runtime_data.async_refresh()

    # Charging status should still be charging
    state = hass.states.get("sensor.smart_charging_status")
    assert state
    assert state.state == "charging"

    # Charging power should retain the last valid value (460W) instead of jumping to 0
    state = hass.states.get("sensor.smart_charging_power")
    assert state
    assert state.state == "460.0"

    # Restore valid values to verify sensor can update again
    return_zero = False
    value_target = (230, 3)  # 690W
    await entry.runtime_data.async_refresh()

    # Should now show the new valid value
    state = hass.states.get("sensor.smart_charging_power")
    assert state
    assert state.state == "690.0"
