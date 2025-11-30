"""Support for Smart device tracker."""

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.core import HomeAssistant

from custom_components.smarthashtag.entity import SmartHashtagEntity

from .const import CONF_VEHICLE, LOGGER
from .coordinator import SmartHashtagDataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """
    Set up Smart device tracker entities for smart vehicles.

    This asynchronous function initializes and adds a SmartVehicleLocation entity using the configuration entry's
    runtime data. It retrieves the coordinator from the entry, extracts the vehicle information from the coordinator's
    configuration (using the CONF_VEHICLE key), and schedules the addition of the device tracker with an immediate update.
    Finally, it triggers an asynchronous refresh of the coordinator to update the device state.

    Parameters:
        hass (HomeAssistant): The Home Assistant instance.
        entry (ConfigEntry): Configuration entry that contains runtime data for the device tracker.
        async_add_entities (Callable[[List[Entity], bool], None]): Function to add device tracker entities to Home Assistant.
            The entity is added with update_before_add set to True.

    Returns:
        None
    """
    coordinator = entry.runtime_data
    vehicle = coordinator.config_entry.data.get(CONF_VEHICLE)

    async_add_entities(
        [SmartVehicleLocation(coordinator, vehicle)], update_before_add=True
    )
    await coordinator.async_request_refresh()


class SmartVehicleLocation(SmartHashtagEntity, TrackerEntity):
    """Representation of a Smart vehicle location device tracker."""

    type = "location tracker"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SmartHashtagDataUpdateCoordinator,
        vehicle: str,
    ) -> None:
        """Initialize the device_tracker class."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_location"
        self.coordinator = coordinator
        self._vehicle = vehicle
        self.name = f"Smart {vehicle}"

    @property
    def source_type(self):
        """Return device tracker source type."""
        return SourceType.GPS

    @property
    def longitude(self):
        """Return longitude."""
        try:
            if self.coordinator.data is None:
                return None
            vehicle = self.coordinator.data.get(self._vehicle)
            if vehicle is None:
                return None
            return vehicle.position.longitude / 3600000
        except AttributeError as err:
            LOGGER.error("AttributeError getting longitude: %s", err)
            return None

    @property
    def latitude(self):
        """Return latitude."""
        try:
            if self.coordinator.data is None:
                return None
            vehicle = self.coordinator.data.get(self._vehicle)
            if vehicle is None:
                return None
            return vehicle.position.latitude / 3600000
        except AttributeError as err:
            LOGGER.error("AttributeError getting latitude: %s", err)
            return None

    @property
    def extra_state_attributes(self):
        """Return device state attributes."""
        altitude = None
        position_can_be_trusted = None
        try:
            if self.coordinator.data is not None:
                vehicle = self.coordinator.data.get(self._vehicle)
                if vehicle is not None:
                    altitude = vehicle.position.altitude
                    position_can_be_trusted = vehicle.position.position_can_be_trusted
        except AttributeError as err:
            LOGGER.error("AttributeError getting extra_state_attributes: %s", err)
        return {
            "altitude": altitude,
            "position_can_be_trusted": position_can_be_trusted,
        }

    @property
    def force_update(self):
        """Disable forced updated since we are polling via the coordinator updates."""
        return False

    @property
    def battery_level(self) -> int | None:
        """Return the battery level of the device.

        Percentage from 0-100.
        """
        try:
            if self.coordinator.data is None:
                return None
            vehicle = self.coordinator.data.get(self._vehicle)
            if vehicle is None:
                return None
            return vehicle.battery.remaining_battery_percent.value
        except AttributeError as err:
            LOGGER.error("AttributeError getting battery_level: %s", err)
            return None
