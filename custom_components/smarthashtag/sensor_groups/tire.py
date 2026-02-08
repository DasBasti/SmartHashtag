"""Tire-related sensor entity descriptions."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
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
