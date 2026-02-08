"""Support for Smart selects."""

from typing import Literal

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from pysmarthashtag.control.climate import HeatingLocation

from . import SmartHashtagConfigEntry
from .const import CONF_VEHICLE, LOGGER
from .coordinator import SmartHashtagDataUpdateCoordinator

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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartHashtagConfigEntry,
    async_add_entities,
) -> None:
    """
    Set up Smart Select entities for vehicle heating controls.

    This asynchronous function initializes Smart Pre-Heated Location entities for each
    available heating location defined in the HeatingLocation enumeration. It retrieves the
    coordinator from the configuration entry's runtime data and extracts the vehicle details
    from the coordinator's configuration data using the CONF_VEHICLE key. The created
    entities are then registered with Home Assistant via the async_add_entities callback,
    which updates the entities before they are added.

    Parameters:
        hass (HomeAssistant): The Home Assistant instance.
        entry (SmartHashtagConfigEntry): The configuration entry containing runtime data for
            the smart hashtag integration.
        async_add_entities (Callable): A callback function to add entities to Home Assistant.
            The entities will be updated before being added.

    Returns:
        None
    """
    coordinator = entry.runtime_data
    vehicle = coordinator.config_entry.data.get(CONF_VEHICLE)
    entities = []

    vehicles = coordinator.account.vehicles or {}
    if vehicle not in vehicles:
        LOGGER.error("Vehicle %s not available; skipping select setup", vehicle)
        return

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
        self._vehicle_vin = vehicle
        self._vehicle = self.coordinator.account.vehicles.get(vehicle)
        if self._vehicle is None:
            LOGGER.error(
                "Vehicle %s not available for preheating select", self._vehicle_vin
            )
            self._attr_available = False
            return
        self._attr_name = (
            f"Smart {vehicle} Conditioning {HEATING_LOCATION_NAMES[location]}"
        )
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_preconditioning_{HEATING_LOCATION_NAMES[location].lower().replace(' ', '_')}"
        self._location = location
        self.entity_description = SELECT_DESCRIPTIONS[location]

        # reload the last selected level
        try:
            self._vehicle.climate_control.set_heating_level(
                self._location, self._get_level_for_location(self._location)
            )
        except Exception as e:
            LOGGER.warning("Failed to set initial heating level: %s", str(e))

    def _get_level_for_location(self, location: HeatingLocation) -> Literal[0, 1, 2, 3]:
        """Get the heating level for the specified location."""
        if (
            self.coordinator.config_entry
            and "selects" in self.coordinator.config_entry.data
        ):
            level = self.coordinator.config_entry.data["selects"].get(location.value, 0)
            return level
        else:
            LOGGER.debug("No heating level found for %s", location)
        return 0

    async def async_select_option(self, option: str, **kwargs):
        """Change the selected option."""
        if self._vehicle is None:
            LOGGER.warning(
                "Cannot set option %s; vehicle %s unavailable", option, self._vehicle_vin
            )
            return

        level: int = HEATING_LEVEL_OPTIONS_MAP[option]
        self._vehicle.climate_control.set_heating_level(self._location, level)

        # save the selected level
        new_data = self.coordinator.config_entry.data.copy()
        if "selects" not in new_data:
            new_data["selects"] = {}
        else:
            # Create a copy of the nested selects dict to avoid mutating the original
            new_data["selects"] = new_data["selects"].copy()
        new_data["selects"][self._location.value] = level
        self.hass.config_entries.async_update_entry(
            self.coordinator.config_entry, data=new_data
        )
        LOGGER.debug(f"Setting {self._location} to %s", level)

    @property
    def current_option(self) -> str:
        """Return current heated steering setting."""
        if self._vehicle is None:
            return STEERING_HEATER_OPTIONS[0]

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

        if current_str is None:
            LOGGER.warning("Unknown heating level: %s", current_value)
            return STEERING_HEATER_OPTIONS[0]
        options_idx = STEERING_HEATER_OPTIONS.index(current_str)

        return STEERING_HEATER_OPTIONS[options_idx]

    @property
    def options(self):
        """Return heated seat options."""
        return STEERING_HEATER_OPTIONS
