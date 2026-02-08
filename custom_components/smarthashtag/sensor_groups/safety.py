"""Safety-related sensor entity descriptions."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.const import EntityCategory

ENTITY_SAFETY_DESCRIPTIONS = (
    # NOTE: Seatbelt sensors may not report accurate values on Smart #3 vehicles.
    # The Smart API does not reliably update seatbelt status data.
    # See: https://github.com/DasBasti/SmartHashtag/issues/287
    SensorEntityDescription(
        key="seat_belt_status_driver",
        translation_key="seat_belt_status_driver",
        name="Seat belt status driver",
        icon="mdi:seatbelt",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="seat_belt_status_driver_rear",
        translation_key="seat_belt_status_driver_rear",
        name="Seat belt status driver rear",
        icon="mdi:seatbelt",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="seat_belt_status_mid_rear",
        translation_key="seat_belt_status_mid_rear",
        name="Seat belt status mid rear",
        icon="mdi:seatbelt",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="seat_belt_status_passenger",
        translation_key="seat_belt_status_passenger",
        name="Seat belt status passenger",
        icon="mdi:seatbelt",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="seat_belt_status_passenger_rear",
        translation_key="seat_belt_status_passenger_rear",
        name="Seat belt status passenger rear",
        icon="mdi:seatbelt",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="seat_belt_status_th_driver_rear",
        translation_key="seat_belt_status_th_driver_rear",
        name="Seat belt status th driver rear",
        icon="mdi:seatbelt",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="seat_belt_status_th_passenger_rear",
        translation_key="seat_belt_status_th_passenger_rear",
        name="Seat belt status th passenger rear",
        icon="mdi:seatbelt",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
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
