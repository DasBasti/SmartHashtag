"""Sensor platform for Smar #1/#3 intergration."""

from __future__ import annotations

import dataclasses
from datetime import timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from pysmarthashtag.models import ValueWithUnit

from .const import (
    CONF_CHARGING_INTERVAL,
    CONF_DRIVING_INTERVAL,
    CONF_VEHICLE,
    DEFAULT_CHARGING_INTERVAL,
    DEFAULT_DRIVING_INTERVAL,
    LOGGER,
)
from .coordinator import SmartHashtagDataUpdateCoordinator
from .entity import SmartHashtagEntity

ENTITY_BATTERY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="remaining_range",
        translation_key="remaining_range",
        name="Remaining Range",
        icon="mdi:road-variant",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="km",
    ),
    SensorEntityDescription(
        key="remaining_range_at_full_charge",
        translation_key="remaining_range_at_full_charge",
        name="Remaining Range at full battery",
        icon="mdi:road-variant",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="km",
    ),
    SensorEntityDescription(
        key="remaining_battery_percent",
        translation_key="remaining_battery_percent",
        name="Remaining battery charge",
        icon="mdi:percent",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="charging_status",
        translation_key="charging_status",
        name="Charging status",
        icon="mdi:power-plug-battery",
        options={
            "charging": "charging",
            "complete": "fully charged",
            "dc_charging": "DC charging",
            "default": "default",
            "not_charging": "not charging",
        },
        device_class=SensorDeviceClass.ENUM,
    ),
    SensorEntityDescription(
        key="charging_status_raw",
        translation_key="charging_status_raw",
        name="Charging status_raw",
        icon="mdi:power-plug-battery",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="charger_connection_status",
        translation_key="charger_connection_status",
        name="Charger connection status",
        icon="mdi:battery-unknown",
        options={
            0: "not connected",
            1: "tbd",
            2: "plugged, not charging",
            3: "charging",
        },
        device_class=SensorDeviceClass.ENUM,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="is_charger_connected",
        translation_key="is_charger_connected",
        name="is charger connected",
        icon="mdi:power-plug-battery",
    ),
    SensorEntityDescription(
        key="charging_voltage",
        translation_key="charging_voltage",
        name="Charging voltage",
        icon="mdi:car-battery",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="charging_current",
        translation_key="charging_current",
        name="Charging current",
        icon="mdi:car-battery",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement="A",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="charging_power",
        translation_key="charging_power",
        name="Charging power",
        icon="mdi:car-battery",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement="W",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="charging_time_remaining",
        translation_key="charging_time_remaining",
        name="Charging time remaining",
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="min",
    ),
    SensorEntityDescription(
        key="charging_target_soc",
        translation_key="charging_target_soc",
        name="Target state of charge",
        icon="mdi:percent",
        device_class=SensorDeviceClass.BATTERY,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="average_power_consumption",
        translation_key="average_power_consumption",
        name="Average power consumption",
        icon="mdi:power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
)

# FIXME: Find out how the position is handled in HA
ENTITY_POSITION_DESCRIPTIONS = (
    SensorEntityDescription(
        key="position",
        translation_key="position",
        name="Postion",
        icon="mdi:map-marker",
    ),
    SensorEntityDescription(
        key="position_can_be_trusted",
        translation_key="position_can_be_trusted",
        name="Position can be trusted",
        icon="mdi:map-marker-alert",
    ),
)


ENTITY_TIRE_DESCRIPTIONS = (
    SensorEntityDescription(
        key="temperature_0",
        translation_key="temperature_0",
        name="Tire temperature driver front",
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement="°C",
        entity_registry_enabled_default=False,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="temperature_1",
        translation_key="temperature_1",
        name="Tire temperature driver rear",
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement="°C",
        entity_registry_enabled_default=False,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="temperature_2",
        translation_key="temperature_2",
        name="Tire temperature passender front",
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement="°C",
        entity_registry_enabled_default=False,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="temperature_3",
        translation_key="temperature_3",
        name="Tire temperature passenger rear",
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement="°C",
        entity_registry_enabled_default=False,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="tire_pressure_0",
        translation_key="tire_pressure_0",
        name="Tire pressure front driver",
        icon="mdi:gauge",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement="hPa",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="tire_pressure_1",
        translation_key="tire_pressure_1",
        name="Tire pressure rear driver",
        icon="mdi:gauge",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement="hPa",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="tire_pressure_2",
        translation_key="tire_pressure_2",
        name="Tire pressure front passenger",
        icon="mdi:gauge",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement="hPa",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="tire_pressure_3",
        translation_key="tire_pressure_3",
        name="Tire pressure rear passenger",
        icon="mdi:gauge",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement="hPa",
        state_class=SensorStateClass.MEASUREMENT,
    ),
)

ENTITY_MAINTENANCE_DESCRIPTIONS = (
    SensorEntityDescription(
        key="main_battery_state_of_charge",
        translation_key="main_battery_state_of_charge",
        name="Main battery state of charge",
        icon="mdi:car-battery",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="main_battery_charge_level",
        translation_key="main_battery_charge_level",
        name="Main battery charge level",
        icon="mdi:car-battery",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="main_battery_energy_level",
        translation_key="main_battery_energy_level",
        name="Main battery energy level",
        icon="mdi:car-battery",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="main_battery_state_of_health",
        translation_key="main_battery_state_of_health",
        name="Main battery state of health",
        icon="mdi:car-battery",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="main_batter_power_level",
        translation_key="main_batter_power_level",
        name="Main battery power level",
        icon="mdi:car-battery",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="main_battery_voltage",
        translation_key="main_battery_voltage",
        name="Main battery voltage",
        icon="mdi:car-battery",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="V",
    ),
    SensorEntityDescription(
        key="odometer",
        translation_key="odometer",
        name="Odometer",
        icon="mdi:counter",
        device_class=SensorDeviceClass.DISTANCE,
        # The sensor's value never goes backward
        # https://developers.home-assistant.io/docs/core/entity/sensor/#how-to-choose-state_class-and-last_reset
        state_class=SensorStateClass.TOTAL_INCREASING,
        last_reset=None,
        native_unit_of_measurement="km",
    ),
    SensorEntityDescription(
        key="days_to_service",
        translation_key="days_to_service",
        name="Service due in",
        icon="mdi:calendar-check",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="d",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="engine_hours_to_service",
        translation_key="engine_hours_to_service",
        name="Service due in",
        icon="mdi:calendar-check",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="h",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="distance_to_service",
        translation_key="distance_to_service",
        name="Service due in",
        icon="mdi:calendar-check",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement="km",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="break_fluid_level_status",
        translation_key="break_fluid_level_status",
        name="Break fluid level status",
        icon="mdi:car-brake-fluid-level",
    ),
    SensorEntityDescription(
        key="washer_fluid_level_status",
        translation_key="washer_fluid_level_status",
        name="Washer fluid level status",
        icon="mdi:wiper-wash",
    ),
    SensorEntityDescription(
        key="service_warning_status",
        translation_key="service_warning_status",
        name="Service warning status",
        icon="mdi:account-wrench",
    ),
)

ENTITY_GENERAL_DESCRIPTIONS = (
    SensorEntityDescription(
        key="last_update",
        translation_key="last_update",
        name="Last update",
        icon="mdi:update",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="engine_state",
        translation_key="engine_state",
        name="Engine state",
        icon="mdi:engine-off",
    ),
)

ENTITY_RUNNING_DESCRIPTIONS = (
    SensorEntityDescription(
        key="ahbc_status",
        translation_key="ahbc_status",
        name="Adaptive high beam control",
        icon="mdi:car-parking-lights",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="goodbye",
        translation_key="goodbye",
        name="Goodbye Light",
        icon="mdi:car-parking-lights",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="home_safe",
        translation_key="home_safe",
        name="Home Safe Light",
        icon="mdi:car-parking-lights",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="corner_light",
        translation_key="corner_light",
        name="Corner Light",
        icon="mdi:car-parking-lights",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="front_fog_light",
        translation_key="front_fog_light",
        name="Front Fog Light",
        icon="mdi:car-parking-lights",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="stop_light",
        translation_key="stop_light",
        name="Stop Light",
        icon="mdi:car-parking-lights",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="trip_meter1",
        translation_key="trip_meter1",
        name="Trip meter 1",
        icon="mdi:counter",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="km",
    ),
    SensorEntityDescription(
        key="trip_meter2",
        translation_key="trip_meter2",
        name="Trip meter 2",
        icon="mdi:counter",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="km",
    ),
    SensorEntityDescription(
        key="approach",
        translation_key="approach",
        name="Approach Light",
        icon="mdi:car-parking-lights",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="high_beam",
        translation_key="high_beam",
        name="High Beam Light",
        icon="mdi:car-parking-lights",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="engine_coolant_level_status",
        translation_key="engine_coolant_level_status",
        name="Engine coolant level status",
        icon="mdi:car-coolant-level",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="low_beam",
        translation_key="low_beam",
        name="Low Beam Light",
        icon="mdi:car-parking-lights",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="position_light_rear",
        translation_key="position_light_rear",
        name="Position Light Rear",
        icon="mdi:car-parking-lights",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="light_show",
        translation_key="light_show",
        name="Light Show",
        icon="mdi:car-parking-lights",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="welcome",
        translation_key="welcome",
        name="Welcome Light",
        icon="mdi:car-parking-lights",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="drl",
        translation_key="drl",
        name="Daytime running light",
        icon="mdi:car-parking-lights",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="ahl",
        translation_key="ahl",
        name="Adaptive headlight",
        icon="mdi:car-parking-lights",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="trun_indicator_left",
        translation_key="turn_indicator_left",
        name="Turn indicator left",
        icon="mdi:car-parking-lights",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="trun_indicator_right",
        translation_key="turn_indicator_right",
        name="Turn indicator right",
        icon="mdi:car-parking-lights",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="adaptive_front_light",
        translation_key="adaptive_front_light",
        name="Adaptive front light",
        icon="mdi:car-parking-lights",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="dbl",
        translation_key="dbl",
        name="Double Light",
        icon="mdi:car-parking-lights",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="average_speed",
        translation_key="average_speed",
        name="Average speed",
        icon="mdi:speedometer",
        device_class=SensorDeviceClass.SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="km/h",
    ),
    SensorEntityDescription(
        key="position_light_front",
        translation_key="position_light_front",
        name="Position Light Front",
        icon="mdi:car-parking-lights",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="reverse_light",
        translation_key="reverse_light",
        name="Reverse Light",
        icon="mdi:car-parking-lights",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="highway_light",
        translation_key="highway_light",
        name="Highway Light",
        icon="mdi:car-parking-lights",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="rear_fog_light",
        translation_key="rear_fog_light",
        name="Rear Fog Light",
        icon="mdi:car-parking-lights",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="flash_light",
        translation_key="flash_light",
        name="Flash Light",
        icon="mdi:car-parking-lights",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="all_weather_light",
        translation_key="all_weather_light",
        name="All Weather Light",
        icon="mdi:car-parking-lights",
        entity_registry_enabled_default=False,
    ),
)

ENTITY_CLIMATE_DESCRIPTIONS = (
    SensorEntityDescription(
        key="air_blower_active",
        translation_key="air_blower_active",
        name="Air blower active",
        icon="mdi:fan",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="cds_climate_active",
        translation_key="cds_climate_active",
        name="CDS climate active",
        icon="mdi:snowflake",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="climate_over_heat_protection_active",
        translation_key="climate_over_heat_protection_active",
        name="Climate over heat protection active",
        icon="mdi:thermostat",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="curtain_open_status",
        translation_key="curtain_open_status",
        name="Curtain open status",
        icon="mdi:curtains",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="defrosting_active",
        translation_key="defrosting_active",
        name="Defrosting active",
        icon="mdi:snowflake",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="driver_heating_detail",
        translation_key="driver_heating_detail",
        name="Driver heating detail",
        icon="mdi:fan",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="driver_heating_status",
        translation_key="driver_heating_status",
        name="Driver heating status",
        icon="mdi:fan",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="driver_ventilation_detail",
        translation_key="driver_ventilation_detail",
        name="Driver ventilation detail",
        icon="mdi:fan",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="driver_ventilation_status",
        translation_key="driver_ventilation_status",
        name="Driver ventilation status",
        icon="mdi:fan",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="exterior_temperature",
        translation_key="exterior_temperature",
        name="Exterior temperature",
        icon="mdi:home-thermometer-outline",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="frag_active",
        translation_key="frag_active",
        name="FRAG active",
        icon="mdi:chat-question-outline",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="interior_temperature",
        translation_key="interior_temperature",
        name="Interior temperature",
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="passenger_heating_detail",
        translation_key="passenger_heating_detail",
        name="Passenger heating detail",
        icon="mdi:fan",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="passenger_heating_status",
        translation_key="passenger_heating_status",
        name="Passenger heating status",
        icon="mdi:fan",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="passenger_ventilation_detail",
        translation_key="passenger_ventilation_detail",
        name="Passenger ventilation detail",
        icon="mdi:fan",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="passenger_ventilation_status",
        translation_key="passenger_ventilation_status",
        name="Passenger ventilation status",
        icon="mdi:fan",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="pre_climate_active",
        translation_key="pre_climate_active",
        name="Pre climate active",
        icon="mdi:heat-pump-outline",
    ),
    SensorEntityDescription(
        key="rear_left_heating_detail",
        translation_key="rear_left_heating_detail",
        name="Rear left heating detail",
        icon="mdi:heat-pump-outline",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="rear_left_heating_status",
        translation_key="rear_left_heating_status",
        name="Rear left heating status",
        icon="mdi:heat-pump-outline",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="rear_left_ventilation_detail",
        translation_key="rear_left_ventilation_detail",
        name="Rear left ventilation detail",
        icon="mdi:fan",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="rear_left_ventilation_status",
        translation_key="rear_left_ventilation_status",
        name="Rear left ventilation status",
        icon="mdi:fan",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="rear_right_heating_detail",
        translation_key="rear_right_heating_detail",
        name="Rear right heating detail",
        icon="mdi:heat-pump-outline",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="rear_right_heating_status",
        translation_key="rear_right_heating_status",
        name="Rear right heating status",
        icon="mdi:heat-pump-outline",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="rear_right_ventilation_detail",
        translation_key="rear_right_ventilation_detail",
        name="Rear right ventilation detail",
        icon="mdi:fan",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="rear_right_ventilation_status",
        translation_key="rear_right_ventilation_status",
        name="Rear right ventilation status",
        icon="mdi:fan",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="steering_wheel_heating_status",
        translation_key="steering_wheel_heating_status",
        name="Steering wheel heating status",
        icon="mdi:steering",
    ),
    SensorEntityDescription(
        key="sun_curtain_rear_open_status",
        translation_key="sun_curtain_rear_open_status",
        name="Sun curtain rear open status",
        icon="mdi:curtains",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="sun_curtain_rear_position",
        translation_key="sun_curtain_rear_position",
        name="Sun curtain rear position",
        icon="mdi:curtains",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="sunroof_open_status",
        translation_key="sunroof_open_status",
        name="Sunroof open status",
        icon="mdi:window-shutter",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="sunroof_position",
        translation_key="sunroof_position",
        name="Sunroof position",
        icon="mdi:window-shutter",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="window_driver_position",
        translation_key="window_driver_position",
        name="Window driver position",
        icon="mdi:window-open",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="window_driver_rear_position",
        translation_key="window_driver_rear_position",
        name="Window driver rear position",
        icon="mdi:window-open",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="window_passenger_position",
        translation_key="window_passenger_position",
        name="Window passenger position",
        icon="mdi:window-open",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="window_passenger_rear_position",
        translation_key="window_passenger_rear_position",
        name="Window passenger rear position",
        icon="mdi:window-open",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="window_driver_status",
        translation_key="window_driver_status",
        name="Window driver status",
        icon="mdi:window-open",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="window_driver_rear_status",
        translation_key="window_driver_rear_status",
        name="Window driver rear status",
        icon="mdi:window-open",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="window_passenger_status",
        translation_key="window_passenger_status",
        name="Window passenger status",
        icon="mdi:window-open",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="window_passenger_rear_status",
        translation_key="window_passenger_rear_status",
        name="Window passenger rear status",
        icon="mdi:window-open",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="interior_PM25",
        translation_key="interior_pm25",
        name="Interior PM25",
        icon="mdi:air-filter",
        entity_registry_enabled_default=False,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="relative_humidity",
        translation_key="relative_humidity",
        name="Relative humidity",
        icon="mdi:water-percent",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        entity_registry_enabled_default=False,
    ),
)

ENTITY_SAFETY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="seat_belt_status_driver",
        translation_key="seat_belt_status_driver",
        name="Seat belt status driver",
        icon="mdi:seatbelt",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="seat_belt_status_driver_rear",
        translation_key="seat_belt_status_driver_rear",
        name="Seat belt status driver rear",
        icon="mdi:seatbelt",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="seat_belt_status_mid_rear",
        translation_key="seat_belt_status_mid_rear",
        name="Seat belt status mid rear",
        icon="mdi:seatbelt",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="seat_belt_status_passenger",
        translation_key="seat_belt_status_passenger",
        name="Seat belt status passenger",
        icon="mdi:seatbelt",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="seat_belt_status_passenger_rear",
        translation_key="seat_belt_status_passenger_rear",
        name="Seat belt status passenger rear",
        icon="mdi:seatbelt",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="seat_belt_status_th_driver_rear",
        translation_key="seat_belt_status_th_driver_rear",
        name="Seat belt status th driver rear",
        icon="mdi:seatbelt",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="seat_belt_status_th_passenger_rear",
        translation_key="seat_belt_status_th_passenger_rear",
        name="Seat belt status th passenger rear",
        icon="mdi:seatbelt",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="srs_crash_status",
        translation_key="srs_crash_status",
        name="SRS crash status",
        icon="mdi:car-brake-alert",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="tank_flap_status",
        translation_key="tank_flap_status",
        name="Tank flap status",
        icon="mdi:gas-station",
        entity_registry_enabled_default=False,
    ),
)


def remove_vin_from_key(key: str) -> str:
    """Remove the vin from the key."""
    return "_".join(key.split("_")[1:])


def vin_from_key(key: str) -> str:
    """Get the vin from the key."""
    return key.split("_")[0]


async def async_setup_entry(hass, entry, async_add_devices):
    """
    Initialize the Smart Hashtag sensor platform for Home Assistant.

    This asynchronous function sets up and registers sensor devices for a Smart Hashtag vehicle by iterating over
    multiple predefined sensor entity descriptions. It retrieves the coordinator from the configuration entry’s runtime data,
    extracts the vehicle identifier from the coordinator’s configuration, and creates sensor instances with updated entity
    descriptions that incorporate the vehicle identifier. The sensors added include battery range, tire, general update,
    maintenance, running, climate, and safety sensors.

    Parameters:
        hass (HomeAssistant): The Home Assistant instance.
        entry (ConfigEntry): The configuration entry that provides integration-specific data, including runtime data and
            the vehicle configuration.
        async_add_devices (Callable[[Iterable[SensorEntity]], None]): A callback function used to add the sensor entities
            to Home Assistant.

    Returns:
        None

    Example:
        await async_setup_entry(hass, entry, async_add_devices)
    """
    coordinator = entry.runtime_data
    vehicle = coordinator.config_entry.data.get(CONF_VEHICLE)

    async_add_devices(
        SmartHashtagBatteryRangeSensor(
            coordinator=coordinator,
            entity_description=dataclasses.replace(
                entity_description, key=f"{vehicle}_{entity_description.key}"
            ),
        )
        for entity_description in ENTITY_BATTERY_DESCRIPTIONS
    )

    async_add_devices(
        SmartHashtagTireSensor(
            coordinator=coordinator,
            entity_description=dataclasses.replace(
                entity_description, key=f"{vehicle}_{entity_description.key}"
            ),
        )
        for entity_description in ENTITY_TIRE_DESCRIPTIONS
    )

    async_add_devices(
        SmartHashtagUpdateSensor(
            coordinator=coordinator,
            entity_description=dataclasses.replace(
                entity_description, key=f"{vehicle}_{entity_description.key}"
            ),
        )
        for entity_description in ENTITY_GENERAL_DESCRIPTIONS
    )

    async_add_devices(
        SmartHashtagMaintenanceSensor(
            coordinator=coordinator,
            entity_description=dataclasses.replace(
                entity_description, key=f"{vehicle}_{entity_description.key}"
            ),
        )
        for entity_description in ENTITY_MAINTENANCE_DESCRIPTIONS
    )

    async_add_devices(
        SmartHashtagRunningSensor(
            coordinator=coordinator,
            entity_description=dataclasses.replace(
                entity_description, key=f"{vehicle}_{entity_description.key}"
            ),
        )
        for entity_description in ENTITY_RUNNING_DESCRIPTIONS
    )

    async_add_devices(
        SmartHashtagClimateSensor(
            coordinator=coordinator,
            entity_description=dataclasses.replace(
                entity_description, key=f"{vehicle}_{entity_description.key}"
            ),
        )
        for entity_description in ENTITY_CLIMATE_DESCRIPTIONS
    )

    async_add_devices(
        SmartHashtagSafetySensor(
            coordinator=coordinator,
            entity_description=dataclasses.replace(
                entity_description, key=f"{vehicle}_{entity_description.key}"
            ),
        )
        for entity_description in ENTITY_SAFETY_DESCRIPTIONS
    )


class SmartHashtagBatteryRangeSensor(SmartHashtagEntity, SensorEntity):
    """Battery Sensor class."""

    def __init__(
        self,
        coordinator: SmartHashtagDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._attr_unique_id}_{entity_description.key}"
        self.entity_description = entity_description

    @property
    def native_value(self) -> int:
        """Return the native value of the sensor."""
        try:
            data = getattr(
                self.coordinator.account.vehicles.get(
                    vin_from_key(self.entity_description.key)
                ).battery,
                remove_vin_from_key(self.entity_description.key),
            )

            if "charging_current" in self.entity_description.key:
                if data.value != 0:
                    self.coordinator.set_update_interval(
                        "charging",
                        timedelta(
                            seconds=self.coordinator.config_entry.options.get(
                                CONF_CHARGING_INTERVAL, DEFAULT_CHARGING_INTERVAL
                            )
                        ),
                    )
                    self.hass.async_create_task(
                        self.coordinator.async_request_refresh()
                    )
                else:
                    self.coordinator.reset_update_interval("charging")

            if "charging_power" in self.entity_description.key:
                if data.value == -0.0:
                    return 0.0

            if "charging_status" in self.entity_description.key:
                if isinstance(data, str):
                    data = data.lower()
                return data

            # invert power consumption value to display the consumed power as positive
            if "average_power_consumption" in self.entity_description.key:
                if data.value:
                    return data.value * -1
                return data

            if isinstance(data, ValueWithUnit):
                return data.value

            return data

        except AttributeError as err:
            LOGGER.error(
                "AttributeError value: %s (%s)", self.entity_description.key, err
            )
            return self._last_value

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement of the sensor."""
        data = getattr(
            self.coordinator.account.vehicles.get(
                vin_from_key(self.entity_description.key)
            ).battery,
            remove_vin_from_key(self.entity_description.key),
        )
        if "charging_status" in self.entity_description.key:
            return None
        if isinstance(data, ValueWithUnit):
            return data.unit

        return data


class SmartHashtagTireSensor(SmartHashtagEntity, SensorEntity):
    """Tire Status class."""

    def __init__(
        self,
        coordinator: SmartHashtagDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._attr_unique_id}_{entity_description.key}"
        self.entity_description = entity_description

    @property
    def native_value(self) -> float:
        """Return the native value of the sensor."""
        try:
            key = "_".join(self.entity_description.key.split("_")[1:-1])
            tire_idx = int(self.entity_description.key.split("_")[-1])
            return getattr(
                self.coordinator.account.vehicles.get(
                    vin_from_key(self.entity_description.key)
                ).tires,
                key,
            )[tire_idx].value

        except AttributeError as err:
            LOGGER.error(
                "AttributeError value: %s (%s)", self.entity_description.key, err
            )
            return self._last_value

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement of the sensor."""
        key = "_".join(self.entity_description.key.split("_")[1:-1])
        tire_idx = int(self.entity_description.key.split("_")[-1])
        data = getattr(
            self.coordinator.account.vehicles.get(
                vin_from_key(self.entity_description.key)
            ).tires,
            key,
        )[tire_idx]

        # FIXME: if pysmarthashtag is updated to return the unit as °C remove this
        if data.unit == "C":
            return "°C"

        return data.unit


class SmartHashtagUpdateSensor(SmartHashtagEntity, SensorEntity):
    """Tire Status class."""

    def __init__(
        self,
        coordinator: SmartHashtagDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._attr_unique_id}_{entity_description.key}"
        self.entity_description = entity_description

    @property
    def native_value(self) -> float:
        """Return the native value of the sensor."""
        try:
            key = remove_vin_from_key(self.entity_description.key)
            vin = vin_from_key(self.entity_description.key)
            if key.startswith("service"):
                key = self.entity_description.key.split("_")[-1]
                data = self.coordinator.account.vehicles.get(vin).service[key]
            else:
                data = getattr(
                    self.coordinator.account.vehicles.get(vin),
                    remove_vin_from_key(self.entity_description.key),
                )

            if key == "engine_state":
                if data == "engine_running":
                    self.coordinator.set_update_interval(
                        "driving",
                        timedelta(
                            seconds=self.coordinator.config_entry.options.get(
                                CONF_DRIVING_INTERVAL, DEFAULT_DRIVING_INTERVAL
                            )
                        ),
                    )
                    self.hass.async_create_task(
                        self.coordinator.async_request_refresh()
                    )
                    self.icon = "mdi:engine"
                else:
                    self.coordinator.reset_update_interval("driving")
                    self.icon = "mdi:engine-off"

            if isinstance(data, ValueWithUnit):
                return data.value
            return data

        except AttributeError as err:
            LOGGER.error(
                "AttributeError value: %s (%s)", self.entity_description.key, err
            )
            return self._last_value

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement of the sensor."""
        key = remove_vin_from_key(self.entity_description.key)
        vin = vin_from_key(self.entity_description.key)
        if key.startswith("service"):
            key = key.rsplit("_", maxsplit=1)[-1]
            data = self.coordinator.account.vehicles.get(vin).service[key]
        else:
            data = getattr(
                self.coordinator.account.vehicles.get(vin),
                key,
            )
        if isinstance(data, ValueWithUnit):
            return data.unit
        return self.entity_description.native_unit_of_measurement


class SmartHashtagMaintenanceSensor(SmartHashtagEntity, SensorEntity):
    """Tire Status class."""

    def __init__(
        self,
        coordinator: SmartHashtagDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """
        Initialize the maintenance sensor instance with vehicle data and a unique identifier.

        This constructor extracts the maintenance data for a specific vehicle by using the coordinator's account data.
        It retrieves the vehicle's maintenance information by extracting the VIN from the provided entity description key
        and accessing the corresponding vehicle object. The sensor's unique identifier is then updated by appending the
        entity description key to ensure its distinctiveness.

        Parameters:
            coordinator (SmartHashtagDataUpdateCoordinator): The coordinator that manages data updates and provides access
                to the account's vehicles.
            entity_description (SensorEntityDescription): The sensor's metadata containing the key used to extract the VIN
                and retrieve related maintenance data.

        Returns:
            None
        """
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._attr_unique_id}_{entity_description.key}"
        self.entity_description = entity_description

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        try:
            key = remove_vin_from_key(self.entity_description.key)
            vin = vin_from_key(self.entity_description.key)
            data = getattr(
                self.coordinator.account.vehicles.get(vin).maintenance,
                key,
            )
            if isinstance(data, ValueWithUnit):
                return data.value
            return data

        except AttributeError as err:
            LOGGER.error(
                "AttributeError value: %s (%s)", self.entity_description.key, err
            )
            return None


class SmartHashtagRunningSensor(SmartHashtagEntity, SensorEntity):
    """Tire Status class."""

    def __init__(
        self,
        coordinator: SmartHashtagDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._attr_unique_id}_{entity_description.key}"
        self.entity_description = entity_description

    @property
    def native_value(self) -> float | int | str | None:
        """Return the native value of the sensor."""
        try:
            key = remove_vin_from_key(self.entity_description.key)
            vin = vin_from_key(self.entity_description.key)
            data = getattr(
                self.coordinator.account.vehicles.get(vin).running,
                key,
            )
            if isinstance(data, ValueWithUnit):
                return data.value
            return data

        except AttributeError as err:
            LOGGER.error(
                "AttributeError value: %s (%s)", self.entity_description.key, err
            )
            return self._last_value

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement of the sensor."""
        key = remove_vin_from_key(self.entity_description.key)
        vin = vin_from_key(self.entity_description.key)
        data = getattr(
            self.coordinator.account.vehicles.get(vin).running,
            key,
        )
        if isinstance(data, ValueWithUnit):
            return data.unit
        return self.entity_description.native_unit_of_measurement


class SmartHashtagClimateSensor(SmartHashtagEntity, SensorEntity):
    """Tire Status class."""

    def __init__(
        self,
        coordinator: SmartHashtagDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._attr_unique_id}_{entity_description.key}"
        self.entity_description = entity_description

    @property
    def native_value(self) -> float | int | str | None:
        """Return the native value of the sensor."""
        try:
            key = remove_vin_from_key(self.entity_description.key)
            vin = vin_from_key(self.entity_description.key)
            data = getattr(
                self.coordinator.account.vehicles.get(vin).climate,
                key,
            )
            if isinstance(data, ValueWithUnit):
                return data.value
            return data

        except AttributeError as err:
            LOGGER.error(
                "AttributeError value: %s (%s)", self.entity_description.key, err
            )
            return self._last_value

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement of the sensor."""
        key = remove_vin_from_key(self.entity_description.key)
        vin = vin_from_key(self.entity_description.key)
        data = getattr(
            self.coordinator.account.vehicles.get(vin).climate,
            key,
        )
        if isinstance(data, ValueWithUnit):
            return data.unit
        return self.entity_description.native_unit_of_measurement


class SmartHashtagSafetySensor(SmartHashtagEntity, SensorEntity):
    """Safety class."""

    def __init__(
        self,
        coordinator: SmartHashtagDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._attr_unique_id}_{entity_description.key}"
        self.entity_description = entity_description

    @property
    def native_value(self) -> float | int | str | None:
        """Return the native value of the sensor."""
        try:
            key = remove_vin_from_key(self.entity_description.key)
            vin = vin_from_key(self.entity_description.key)
            data = getattr(
                self.coordinator.account.vehicles.get(vin).safety,
                key,
            )
            if isinstance(data, ValueWithUnit):
                return data.value
            return data

        except AttributeError as err:
            LOGGER.error(
                "AttributeError value: %s (%s)", self.entity_description.key, err
            )
            return self._last_value

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement of the sensor."""
        key = remove_vin_from_key(self.entity_description.key)
        vin = vin_from_key(self.entity_description.key)
        data = getattr(
            self.coordinator.account.vehicles.get(vin).safety,
            key,
        )
        if isinstance(data, ValueWithUnit):
            return data.unit
        return self.entity_description.native_unit_of_measurement
