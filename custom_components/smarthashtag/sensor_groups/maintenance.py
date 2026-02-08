"""Maintenance-related sensor entity descriptions."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
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
