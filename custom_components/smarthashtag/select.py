"""Support for Smart selects."""

from homeassistant.components.select import SelectEntity, SelectEntityDescription
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

HEATING_LEVEL_OPTIONS_MAP = {"Off": 0, "Low": 1, "Mid": 2, "High": 3}
HEATING_LOCATION_NAMES = {
    HeatingLocation.STEERING_WHEEL: "Steering Wheel",
    HeatingLocation.DRIVER_SEAT: "Driver Seat",
    HeatingLocation.PASSENGER_SEAT: "Passenger Seat",
}

SELECT_DESCRIPTIONS = {
    HeatingLocation.STEERING_WHEEL: SelectEntityDescription(
        options=STEERING_HEATER_OPTIONS,
        key="steering_wheel_heater",
        translation_key="steering_wheel_heater",
        name="Steering Wheel Heating",
        icon="mdi:steering",
    ),
    HeatingLocation.DRIVER_SEAT: SelectEntityDescription(
        options=STEERING_HEATER_OPTIONS,
        key="driver_seat_heater",
        translation_key="driver_seat_heater",
        name="Driver Seat Heating",
        icon="mdi:car-seat-heater",
    ),
    HeatingLocation.PASSENGER_SEAT: SelectEntityDescription(
        options=STEERING_HEATER_OPTIONS,
        key="passenger_seat_heater",
        translation_key="passenger_seat_heater",
        name="Passenger Seat Heating",
        icon="mdi:car-seat-heater",
    ),
}


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up the Smart selects by config_entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    vehicle = hass.data[DOMAIN][CONF_VEHICLE]
    entities = []

    for location in HeatingLocation:
        entities.append(SmartPreHeatedLocation(coordinator, vehicle, location))

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
        self._attr_name = (
            f"Smart {vehicle} Conditioning {HEATING_LOCATION_NAMES[location]}"
        )
        self._attr_unique_id = f"{vehicle}_preconditioning_{HEATING_LOCATION_NAMES[location].lower().replace(' ', '_')}"
        self._location = location
        self.entity_description = SELECT_DESCRIPTIONS[location]

        # reload the last selected level
        self._vehicle.climate_control.set_heating_level(
            self._location, self._get_level_for_location(self._location)
        )

    def _get_level_for_location(self, location: HeatingLocation) -> int:
        """Get the heating level for the specified location."""
        if "selects" in self.coordinator.config_entry.data:
            level = self.coordinator.config_entry.data["selects"].get(location, 0)
            return level
        return 0

    def select_option(self, option: str, **kwargs):
        """Change the selected option."""

        async def _update_config_entry(self, new_data):
            self.hass.config_entries.async_update_entry(
                self.coordinator.config_entry, data=new_data
            )

        level: int = HEATING_LEVEL_OPTIONS_MAP[option]
        self._vehicle.climate_control.set_heating_level(self._location, level)

        # save the selected level
        new_data = self.coordinator.config_entry.data.copy()
        if "selects" not in new_data:
            new_data["selects"] = {}
        new_data["selects"][self._location] = level
        self.hass.add_job(_update_config_entry, self, new_data)
        LOGGER.debug(f"Setting {self._location} to %s", level)

    @property
    def current_option(self):
        """Return current heated steering setting."""
        current_value = self._get_level_for_location(self._location)
        self._vehicle.climate_control.set_heating_level(self._location, current_value)
        current_str = next(
            (
                key
                for key, val in HEATING_LEVEL_OPTIONS_MAP.items()
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
