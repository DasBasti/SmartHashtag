"""Sensor platform for Smar #1/#3 intergration."""
from __future__ import annotations


from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from pysmarthashtag.models import ValueWithUnit

from .const import DOMAIN
from .coordinator import SmartHashtagDataUpdateCoordinator
from .entity import SmartHashtagEntity

ENTITY_BATTERY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="remaining_range",
        name="Remaining Range",
        icon="mdi:road-variant",
    ),
    SensorEntityDescription(
        key="remaining_range_at_full_charge",
        name="Remaining Range at full battery",
        icon="mdi:road-variant",
    ),
    SensorEntityDescription(
        key="remaining_battery_percent",
        name="Remaining battery charge",
        icon="mdi:percent",
    ),
    # FIXME: Sort out type issue with None and Strings
    #    SensorEntityDescription(
    #        key="charging_status",
    #        name="Charging status",
    #        icon="mdi:power-plug-battery",
    #    ),
    SensorEntityDescription(
        key="charger_connection_status",
        name="Charger connection status",
        icon="mdi:battery-unknown",
    ),
    SensorEntityDescription(
        key="is_charger_connected",
        name="is charger connected",
        icon="mdi:power-plug-battery",
    ),
    SensorEntityDescription(
        key="charging_voltage",
        name="Charging voltage",
        icon="mdi:car-battery",
    ),
    SensorEntityDescription(
        key="charging_current",
        name="Charging current",
        icon="mdi:car-battery",
    ),
    SensorEntityDescription(
        key="charging_power",
        name="Charging power",
        icon="mdi:car-battery",
    ),
    SensorEntityDescription(
        key="charging_time_remaining",
        name="Charging time remaining",
        icon="mdi:clock-outline",
    ),
    SensorEntityDescription(
        key="charging_target_soc",
        name="Target state of charge",
        icon="mdi:percent",
    ),
)

### FIXME: Find out how the position is handled in HA
ENTITY_POSITION_DESCRIPTIONS = (
    SensorEntityDescription(
        key="position",
        name="Postion",
        icon="mdi:map-marker",
    ),
    SensorEntityDescription(
        key="position_can_be_trusted",
        name="Position can be trusted",
        icon="mdi:map-marker-alert",
    ),
)


ENTITY_TIRE_DESCRIPTIONS = (
    # FIXME: sort out tire module in library
    # SensorEntityDescription(
    #    key="temperature",
    #    name="Tire temperature",
    #    icon="mdi:thermometer",
    #    tires=["driver_front", "driver_rear", "passenger_front", "passenger_rear"],
    # ),
    # FIXME: If 0.1.3 is public use this
    #    SensorEntityDescription(
    #        key="tire_pressure",
    #        name="Tire pressure",
    #        icon="mdi:gauge",
    #        options=["driver_front", "driver_rear", "passenger_front", "passenger_rear"],
    #    ),
)

ENTITY_UPDATE_DESCRIPTIONS = (
    SensorEntityDescription(
        key="last_update",
        name="Last update",
        icon="mdi:update",
    ),
)


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices(
        SmartHashtagBatteryRangeSensor(
            coordinator=coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_BATTERY_DESCRIPTIONS
    )


#    for entity_description in ENTITY_TIRE_DESCRIPTIONS:
#        for idx, tire in enumerate(entity_description.options):
#            this_entity_description = dataclasses.replace(
#                entity_description,
#                key=f"{entity_description.key}_{tire}",
#                tire_idx=idx,
#            )
#            async_add_devices(
#                [
#                    SmartHashtagTireSensor(
#                        coordinator=coordinator,
#                        entity_description=this_entity_description,
#                    )
#                ]
#            )


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
        data = getattr(
            self.coordinator.account.vehicles[0].battery, self.entity_description.key
        )
        if isinstance(data, ValueWithUnit):
            return data.value

        return data

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement of the sensor."""
        data = getattr(
            self.coordinator.account.vehicles[0].battery, self.entity_description.key
        )
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
        return getattr(
            self.coordinator.account.vehicles[0].tires,
            self.entity_description.base_key,
        )[self.entity_description.tire_idx].value

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement of the sensor."""
        return getattr(
            self.coordinator.account.vehicles[0].tires,
            self.entity_description.base_key,
        )[self.entity_description.tire_idx].unit
