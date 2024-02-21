"""Support for Smart device tracker."""

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.core import HomeAssistant

from .coordinator import SmartHashtagDataUpdateCoordinator

from .const import CONF_VEHICLE, DOMAIN, LOGGER


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up the Smart device trackers by config_entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    vehicle = hass.data[DOMAIN][CONF_VEHICLE]

    entities = []

    entities.append(SmartVehicleLocation(coordinator, vehicle))
    LOGGER.debug(f"Adding vehicle {vehicle} to device tracker")
    async_add_entities(entities, update_before_add=True)


class SmartVehicleLocation(TrackerEntity):
    """Representation of a Smart vehicle location device tracker."""

    type = "location tracker"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SmartHashtagDataUpdateCoordinator,
        vehicle: str,
    ) -> None:
        """Initialize the device_tracker class."""
        super().__init__()
        self._attr_unique_id = f"{self._attr_unique_id}_{vehicle}"
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
        longitude: float = (
            self.coordinator.account.vehicles.get(self._vehicle).position.longitude
            / 3600000
        )
        return longitude

    @property
    def latitude(self):
        """Return latitude."""
        latitude: float = (
            self.coordinator.account.vehicles.get(self._vehicle).position.latitude
            / 3600000
        )
        return latitude

    @property
    def extra_state_attributes(self):
        """Return device state attributes."""
        return {
            "altitude": self.coordinator.account.vehicles.get(
                self._vehicle
            ).position.altitude,
            "position_can_be_trusted": self.coordinator.account.vehicles.get(
                self._vehicle
            ).position.position_can_be_trusted,
        }

    @property
    def force_update(self):
        """Disable forced updated since we are polling via the coordinator updates."""
        return False
