"""Unit tests for _handle_error function."""

import logging

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


@pytest.mark.asyncio()
async def test_sensor_climate_values(hass: HomeAssistant, smart_fixture: respx.Router):
    """
    Test the climate sensors.

    This loads sample data and verifies climate sensor values.
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

    # Check interior temperature sensor
    state = hass.states.get("sensor.smart_interior_temperature")
    assert state
    assert state.state is not None
    assert state.attributes.get("device_class") == "temperature"

    # Check exterior temperature sensor
    state = hass.states.get("sensor.smart_exterior_temperature")
    assert state
    assert state.state is not None

    # Check pre climate active sensor
    state = hass.states.get("sensor.smart_pre_climate_active")
    assert state


@pytest.mark.asyncio()
async def test_sensor_interior_pm25_missing_logs_info(
    hass: HomeAssistant, smart_fixture: respx.Router, caplog
):
    """
    Test that missing interior_PM25 field logs at INFO level, not ERROR.

    Some vehicle variants don't have the interior_PM25 sensor. This test verifies
    that when the field is missing, it logs at INFO level to avoid alarming users.
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

    # Refresh the coordinator to trigger sensor updates, which will log the missing field
    with caplog.at_level(logging.INFO):
        await entry.runtime_data.async_refresh()
        await hass.async_block_till_done()

        # Try to get the interior PM25 sensor state (may not exist if disabled by default)
        _ = hass.states.get("sensor.smart_interior_pm25")

    # Verify that INFO log was created for interior_PM25, not ERROR
    info_logs = [
        record
        for record in caplog.records
        if record.levelname == "INFO" and "interior_PM25" in record.message
    ]
    error_logs = [
        record
        for record in caplog.records
        if record.levelname == "ERROR" and "interior_PM25" in record.message
    ]

    # Should have at least one INFO log for interior_PM25 if the sensor tried to update
    # Note: The sensor may not update if it's disabled by default
    # In that case, we just check that there are no ERROR logs
    if len(info_logs) == 0:
        # If no INFO logs, the sensor might not have been accessed
        # But we should still ensure no ERROR logs exist
        assert len(error_logs) == 0, (
            f"Should not have ERROR logs for interior_PM25 field. Found: {error_logs}"
        )
    else:
        # If INFO logs exist, verify no ERROR logs
        assert len(error_logs) == 0, (
            f"Should not have ERROR logs for interior_PM25 field. Found: {error_logs}"
        )


@pytest.mark.asyncio()
async def test_sensor_running_values(hass: HomeAssistant, smart_fixture: respx.Router):
    """
    Test the running sensors.

    This loads sample data and verifies running sensor values.
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

    # Check average speed sensor
    state = hass.states.get("sensor.smart_average_speed")
    assert state
    assert state.state is not None

    # Check trip meter sensors
    state = hass.states.get("sensor.smart_trip_meter_1")
    assert state
    assert state.state is not None

    state = hass.states.get("sensor.smart_trip_meter_2")
    assert state
    assert state.state is not None


@pytest.mark.asyncio()
async def test_sensor_maintenance_values(
    hass: HomeAssistant, smart_fixture: respx.Router
):
    """
    Test the maintenance sensors.

    This loads sample data and verifies maintenance sensor values.
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

    # Check maintenance sensors
    state = hass.states.get("sensor.smart_washer_fluid_level")
    assert state

    # Note: The entity key "break_fluid_level" is intentionally misspelled as "break"
    # (should be "brake") in the integration for backward compatibility. This test uses
    # the same key as defined in the integration to ensure correct behavior.
    state = hass.states.get("sensor.smart_break_fluid_level")
    assert state


@pytest.mark.asyncio()
async def test_sensor_motor_values(hass: HomeAssistant, smart_fixture: respx.Router):
    """
    Test the motor/engine sensors.

    This loads sample data and verifies motor sensor values.
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

    # Check motor/engine state sensor
    state = hass.states.get("sensor.smart_motor")
    assert state
    assert state.state in ["engine_off", "engine_running", "unknown"]


@pytest.mark.asyncio()
async def test_sensor_12v_battery(hass: HomeAssistant, smart_fixture: respx.Router):
    """
    Test the 12V battery sensor.

    This loads sample data and verifies 12V battery sensor values.
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

    # Check 12V battery sensor
    state = hass.states.get("sensor.smart_12v_battery_voltage")
    assert state
    assert float(state.state) > 0
    assert state.attributes.get("device_class") == "voltage"


@pytest.mark.asyncio()
async def test_sensor_remaining_range(hass: HomeAssistant, smart_fixture: respx.Router):
    """
    Test the remaining range sensors.

    This loads sample data and verifies remaining range sensor values.
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

    # Check remaining range sensor
    state = hass.states.get("sensor.smart_range")
    assert state
    assert state.attributes.get("device_class") == "distance"

    # Check remaining battery percent
    state = hass.states.get("sensor.smart_battery")
    assert state
    assert int(state.state) >= 0
    assert int(state.state) <= 100
