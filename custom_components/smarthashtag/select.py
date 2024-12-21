"""Support for Smart selects."""

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant

from pysmarthashtag.control.climate import HeatingLocation

from custom_components.smarthashtag.coordinator import SmartHashtagDataUpdateCoordinator

from .const import CONF_VEHICLE, DOMAIN, LOGGER

STEERING_HEATER_OPTIONS = [
    "Off",
    "Low",
    "Mid",
    "High",
]

STEERING_HEATER_OPTIONS_MAP = {"Off": 0, "Low": 1, "Mid": 2, "High": 3}


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up the Smart selects by config_entry."""
    _ = hass.data[DOMAIN][entry.entry_id]
    coordinator = hass.data[DOMAIN][entry.entry_id]
    vehicle = hass.data[DOMAIN][CONF_VEHICLE]
    entities = []

    entities.append(SmartPreHeatedSteeringWheel(coordinator, vehicle))
    entities.append(
        SmartPreHeatedSeat(coordinator, vehicle, HeatingLocation.DRIVER_SEAT)
    )
    entities.append(
        SmartPreHeatedSeat(coordinator, vehicle, HeatingLocation.PASSENGER_SEAT)
    )

    async_add_entities(entities, update_before_add=True)


class SmartPreHeatedLocation(SelectEntity):
    """Representation of a Smart heated seat / steering wheel select."""

    def __init__(
        self,
        coordinator: SmartHashtagDataUpdateCoordinator,
        vehicle: str,
        location: HeatingLocation,
    ):
        """Initialize heated seat entity."""
        super().__init__()
        self.coordinator = coordinator
        self._vehicle = self.coordinator.account.vehicles[vehicle]
        self._attr_name = f"Smart {vehicle} Conditioning"
        self._attr_unique_id = f"{self._attr_unique_id}_{vehicle}_{location}"
        self._location = location

    def select_option(self, option: str, **kwargs):
        """Change the selected option."""

        level: int = STEERING_HEATER_OPTIONS_MAP[option]
        self._vehicle.climate_control.set_heating_level(self._location, level)
        LOGGER.debug(f"Setting {self._location} to %s", level)

    @property
    def current_option(self):
        """Return current heated steering setting."""
        current_value = self._vehicle.climate_control.heating_levels[self._location]
        current_str = next(
            (
                key
                for key, val in STEERING_HEATER_OPTIONS_MAP.items()
                if val == current_value
            ),
            None,
        )

        options_idx = STEERING_HEATER_OPTIONS.index(current_str)

        return STEERING_HEATER_OPTIONS[options_idx]

    @property
    def options(self):
        """Return heated seat options."""
        return STEERING_HEATER_OPTIONS


class SmartPreHeatedSteeringWheel(SmartPreHeatedLocation):
    """Representation of a Smart heated steering wheel select."""

    type = "heated steering wheel"
    _attr_icon = "mdi:steering"

    def __init__(self, coordinator, vehicle):
        super().__init__(coordinator, vehicle, HeatingLocation.STEERING_WHEEL)


class SmartPreHeatedSeat(SmartPreHeatedLocation):
    """Representation of a Smart heated steering wheel select."""

    type = "heated seat"
    _attr_icon = "mdi:car-seat-heater"

    def __init__(self, coordinator, vehicle, seat):
        super().__init__(coordinator, vehicle, seat)
