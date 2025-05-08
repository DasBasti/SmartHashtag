import dataclasses
from typing import Any, Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from propcache import cached_property

from .const import (
    CONF_VEHICLE,
)
from .coordinator import SmartHashtagDataUpdateCoordinator
from .entity import SmartHashtagEntity
from .sensor import remove_vin_from_key, vin_from_key


@dataclasses.dataclass(frozen=True, kw_only=True)
class SmartHashtagBinarySensorEntityDescription(BinarySensorEntityDescription):
    """A class that enhances Binary Sensor entities."""

    is_on_fn: Callable[[Any], bool]


LOCK_ENTITIES = (
    SmartHashtagBinarySensorEntityDescription(
        key="central_locking_status",
        translation_key="central_locking_status",
        name="Central locking status",
        icon="mdi:lock",
        device_class=BinarySensorDeviceClass.LOCK,
        is_on_fn=lambda state, key: state.safety.central_locking_status == 0,
    ),
    SmartHashtagBinarySensorEntityDescription(
        key="door_lock_status_driver",
        translation_key="door_lock_status_driver",
        name="Door lock status driver",
        icon="mdi:lock",
        device_class=BinarySensorDeviceClass.LOCK,
        entity_registry_enabled_default=False,
        is_on_fn=lambda state, key: state.safety.door_lock_status_driver == 0,
    ),
    SmartHashtagBinarySensorEntityDescription(
        key="door_lock_status_driver_rear",
        translation_key="door_lock_status_driver_rear",
        name="Door lock status driver rear",
        icon="mdi:lock",
        device_class=BinarySensorDeviceClass.LOCK,
        entity_registry_enabled_default=False,
        is_on_fn=lambda state, key: state.safety.door_lock_status_driver_rear == 0,
    ),
    SmartHashtagBinarySensorEntityDescription(
        key="door_lock_status_passenger",
        translation_key="door_lock_status_passenger",
        name="Door lock status passenger",
        icon="mdi:lock",
        device_class=BinarySensorDeviceClass.LOCK,
        entity_registry_enabled_default=False,
        is_on_fn=lambda state, key: state.safety.door_lock_status_passenger == 0,
    ),
    SmartHashtagBinarySensorEntityDescription(
        key="door_lock_status_passenger_rear",
        translation_key="door_lock_status_passenger_rear",
        name="Door lock status passenger rear",
        icon="mdi:lock",
        device_class=BinarySensorDeviceClass.LOCK,
        entity_registry_enabled_default=False,
        is_on_fn=lambda state, key: state.safety.door_lock_status_passenger_rear == 0,
    ),
    SmartHashtagBinarySensorEntityDescription(
        key="door_open_status_driver",
        translation_key="door_open_status_driver",
        name="Door open status driver",
        icon="mdi:door-open",
        device_class=BinarySensorDeviceClass.DOOR,
        entity_registry_enabled_default=False,
        is_on_fn=lambda state, key: state.safety.door_open_status_driver == 0,
    ),
    SmartHashtagBinarySensorEntityDescription(
        key="door_open_status_driver_rear",
        translation_key="door_open_status_driver_rear",
        name="Door open status driver rear",
        icon="mdi:door-open",
        device_class=BinarySensorDeviceClass.DOOR,
        entity_registry_enabled_default=False,
        is_on_fn=lambda state, key: state.safety.door_open_status_driver_rear == 0,
    ),
    SmartHashtagBinarySensorEntityDescription(
        key="door_open_status_passenger",
        translation_key="door_open_status_passenger",
        name="Door open status passenger",
        icon="mdi:door-open",
        device_class=BinarySensorDeviceClass.DOOR,
        entity_registry_enabled_default=False,
        is_on_fn=lambda state, key: state.safety.door_open_status_passenger == 0,
    ),
    SmartHashtagBinarySensorEntityDescription(
        key="door_open_status_passenger_rear",
        translation_key="door_open_status_passenger_rear",
        name="Door open status passenger rear",
        icon="mdi:door-open",
        device_class=BinarySensorDeviceClass.DOOR,
        entity_registry_enabled_default=False,
        is_on_fn=lambda state, key: state.safety.door_open_status_passenger_rear == 0,
    ),
    SmartHashtagBinarySensorEntityDescription(
        key="engine_hood_open_status",
        translation_key="engine_hood_open_status",
        name="Engine hood open status",
        icon="mdi:car-select",
        device_class=BinarySensorDeviceClass.DOOR,
        entity_registry_enabled_default=False,
        is_on_fn=lambda state, key: state.safety.engine_hood_open_status == 0,
    ),
    SmartHashtagBinarySensorEntityDescription(
        key="electric_park_brake_status",
        translation_key="electric_park_brake_status",
        name="Electric park brake status",
        icon="mdi:car-brake-parking",
        device_class=BinarySensorDeviceClass.LOCK,
        entity_registry_enabled_default=False,
        is_on_fn=lambda state, key: state.safety.electric_park_brake_status == 0,
    ),
    SmartHashtagBinarySensorEntityDescription(
        key="trunk_lock_status",
        translation_key="trunk_lock_status",
        name="Trunk lock status",
        device_class=BinarySensorDeviceClass.LOCK,
        icon="mdi:lock",
        is_on_fn=lambda state, key: state.safety.trunk_lock_status == 0,
    ),
    SmartHashtagBinarySensorEntityDescription(
        key="trunk_open_status",
        translation_key="trunk_open_status",
        name="Trunk open status",
        device_class=BinarySensorDeviceClass.DOOR,
        icon="mdi:car-back",
        is_on_fn=lambda state, key: state.safety.trunk_open_status == 0,
    ),
)


class SmartHashtagLockBinaraySensor(SmartHashtagEntity, BinarySensorEntity):
    """Safety Binary Sensor class."""

    def __init__(
        self,
        coordinator: SmartHashtagDataUpdateCoordinator,
        entity_description: SmartHashtagBinarySensorEntityDescription,
    ) -> None:
        """
        Initializes a binary sensor entity for a specific vehicle lock or door status.
        
        Associates the sensor with a data update coordinator and a binary sensor entity description,
        setting a unique identifier based on the entity's key.
        """
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._attr_unique_id}_{entity_description.key}"
        self.entity_description = entity_description

    @cached_property
    def is_on(self) -> bool | None:
        """
        Indicates whether the binary sensor is currently in the "on" state.
        
        Returns:
            True if the associated vehicle component (e.g., door, lock, trunk) is open or unlocked; False if closed or locked; None if the state cannot be determined.
        """
        key = remove_vin_from_key(self.entity_description.key)
        vin = vin_from_key(self.entity_description.key)
        state = self.entity_description.is_on_fn(
            self.coordinator.data[vin],
            key,
        )
        # smart: 0 means open (unlocked), 1 means closed (locked)
        # ha: on means open (True), off means closed (False)
        return state


async def async_setup_entry(hass, entry, async_add_devices):
    """
    Asynchronously sets up binary sensor entities for vehicle lock and door status.
    
    Initializes and adds all lock-related binary sensors for the specified vehicle to Home Assistant when the integration entry is set up.
    """
    coordinator = entry.runtime_data
    vehicle = coordinator.config_entry.data.get(CONF_VEHICLE)

    async_add_devices(
        SmartHashtagLockBinaraySensor(
            coordinator=coordinator,
            entity_description=dataclasses.replace(
                entity_description, key=f"{vehicle}_{entity_description.key}"
            ),
        )
        for entity_description in LOCK_ENTITIES
    )
