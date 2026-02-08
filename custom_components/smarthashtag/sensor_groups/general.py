"""General sensor entity descriptions."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntityDescription

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
