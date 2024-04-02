"""Support for Smart device tracker."""

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.core import HomeAssistant, callback

from custom_components.smarthashtag.entity import SmartHashtagEntity

from .coordinator import SmartHashtagDataUpdateCoordinator

from .const import CONF_VEHICLE, DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up the Smart device trackers by config_entry."""
    coordinator: SmartHashtagDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    vehicle: str = hass.data[DOMAIN][CONF_VEHICLE]

    async_add_entities(
        [SmartVehicleLocation(coordinator, vehicle)], update_before_add=True
    )
    await coordinator.async_request_refresh()


class SmartVehicleLocation(SmartHashtagEntity, TrackerEntity):
    """Representation of a Smart vehicle location device tracker."""

    type = "location tracker"
    _attr_has_entity_name = True
    _longitude: None | float = None
    _latitude: None | float = None
    _altitude: None | float = None

    def __init__(
        self,
        coordinator: SmartHashtagDataUpdateCoordinator,
        vehicle: str,
    ) -> None:
        """Initialize the device_tracker class."""
        super().__init__(coordinator)
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
        return self._longitude

    @property
    def latitude(self):
        """Return latitude."""
        return self._latitude

    @property
    def extra_state_attributes(self):
        """Return device state attributes."""
        return {
            "altitude": self._altitude,
            "position_can_be_trusted": self.coordinator.account.vehicles.get(
                self._vehicle
            ).position.position_can_be_trusted,
        }

    @property
    def force_update(self):
        """Disable forced updated since we are polling via the coordinator updates."""
        return False

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._longitude = (
            self.coordinator.account.vehicles.get(self._vehicle).position.longitude
            / 3600000
        )
        self._latitude = (
            self.coordinator.account.vehicles.get(self._vehicle).position.latitude
            / 3600000
        )
        self._altitude = self.coordinator.account.vehicles.get(
            self._vehicle
        ).position.altitude

        self.async_write_ha_state()

    @callback
    def _async_track_unavailable(self) -> None:
        self.async_write_ha_state()
