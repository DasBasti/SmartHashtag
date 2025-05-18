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
    """
    value_target = (0, 0)

    async def deplete_battery(request: Request, route: respx.Route) -> Response:
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

    _ = hass.states.async_all()

    value_target = (230, 2)
    await entry.runtime_data.async_refresh()

    state = hass.states.get("sensor.smart_charging_status")
    assert state
    assert state.state == "charging"

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
    """
    value_target = 0

    async def deplete_battery(request: Request, route: respx.Route) -> Response:
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

    _ = hass.states.async_all()

    value_target = 100
    await entry.runtime_data.async_refresh()

    state = hass.states.get("sensor.smart_charging_status")
    assert state
    assert state.state == "dc_charging"

    state = hass.states.get("sensor.smart_charging_power")
    assert state
    assert state.state == "41700"

    value_target = 150
    await entry.runtime_data.async_refresh()

    state = hass.states.get("sensor.smart_charging_power")
    assert state
    assert state.state == "62550"
