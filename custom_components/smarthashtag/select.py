"""Support for Smart selects."""

from typing import Literal

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from pysmarthashtag.control.climate import (
    HeatingLocation,
    RearHeatingLocation,
    VentilationLocation,
)

from . import SmartHashtagConfigEntry
from .const import CONF_VEHICLE, LOGGER
from .coordinator import SmartHashtagDataUpdateCoordinator
from .entity import SmartHashtagEntity

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

VENTILATION_LOCATION_NAMES = {
    VentilationLocation.DRIVER_SEAT: "Driver Seat Ventilation",
    VentilationLocation.PASSENGER_SEAT: "Passenger Seat Ventilation",
}
VENTILATION_DESCRIPTIONS = {
    VentilationLocation.DRIVER_SEAT: SelectEntityDescription(
        options=STEERING_HEATER_OPTIONS,
        key="driver_seat_ventilation",
        translation_key="driver_seat_ventilation",
        name="Driver Seat Ventilation",
        icon="mdi:car-seat-cooler",
    ),
    VentilationLocation.PASSENGER_SEAT: SelectEntityDescription(
        options=STEERING_HEATER_OPTIONS,
        key="passenger_seat_ventilation",
        translation_key="passenger_seat_ventilation",
        name="Passenger Seat Ventilation",
        icon="mdi:car-seat-cooler",
    ),
}
REAR_HEATING_LOCATION_NAMES = {
    RearHeatingLocation.REAR_LEFT: "Rear Left Seat",
    RearHeatingLocation.REAR_RIGHT: "Rear Right Seat",
}
REAR_HEATING_DESCRIPTIONS = {
    location: SelectEntityDescription(
        options=STEERING_HEATER_OPTIONS,
        key=f"{location.name.lower()}_seat_heater",
        translation_key=f"{location.name.lower()}_seat_heater",
        name=REAR_HEATING_LOCATION_NAMES[location],
        icon="mdi:car-seat-heater",
    )
    for location in RearHeatingLocation
}
# Config entry "selects" key prefix, so ventilation doesn't clash with heating
VENTILATION_KEY_PREFIX = "ventilation-"

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

    # Seat ventilation exists on the Smart #5 only (ZAF climate format)
    climate_control = vehicles[vehicle].climate_control
    if climate_control is not None and getattr(climate_control, "use_zaf", False):
        for v_location in VentilationLocation:
            entities.append(SmartVentilationLocation(coordinator, vehicle, v_location))
        for r_location in RearHeatingLocation:
            entities.append(SmartRearHeatedLocation(coordinator, vehicle, r_location))

    async_add_entities(entities, update_before_add=True)


class SmartPreHeatedLocation(SmartHashtagEntity, SelectEntity):
    """Representation of a Smart heated seat / steering wheel select."""

    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: SmartHashtagDataUpdateCoordinator,
        vehicle: str,
        location: HeatingLocation,
    ):
        """Initialize heated seat entity."""
        super().__init__(coordinator)
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
                "Cannot set option %s; vehicle %s unavailable",
                option,
                self._vehicle_vin,
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
        if level > 0:
            # heating and ventilation are mutually exclusive per seat
            new_data["selects"].pop(VENTILATION_KEY_PREFIX + self._location.value, None)
        self.hass.config_entries.async_update_entry(
            self.coordinator.config_entry, data=new_data
        )
        LOGGER.debug(f"Setting {self._location} to %s", level)
        self.async_write_ha_state()

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


class SmartVentilationLocation(SmartHashtagEntity, SelectEntity):
    """Saved seat ventilation preference (Smart #5); applied when climate is started."""

    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: SmartHashtagDataUpdateCoordinator,
        vehicle: str,
        location: VentilationLocation,
    ):
        """Initialize ventilated seat entity."""
        super().__init__(coordinator)
        self._vehicle_vin = vehicle
        self._vehicle = self.coordinator.account.vehicles.get(vehicle)
        self._location = location
        self._attr_name = (
            f"Smart {vehicle} Conditioning {VENTILATION_LOCATION_NAMES[location]}"
        )
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_preconditioning_"
            f"{VENTILATION_LOCATION_NAMES[location].lower().replace(' ', '_')}"
        )
        self.entity_description = VENTILATION_DESCRIPTIONS[location]
        self._attr_options = STEERING_HEATER_OPTIONS
        if self._vehicle is None:
            self._attr_available = False

    @property
    def _config_key(self) -> str:
        return VENTILATION_KEY_PREFIX + self._location.value

    def _saved_level(self) -> int:
        selects = self.coordinator.config_entry.data.get("selects", {})
        return selects.get(self._config_key, 0)

    async def async_select_option(self, option: str, **kwargs):
        """Save the preference; this does not start climate control."""
        if self._vehicle is None:
            return
        level = HEATING_LEVEL_OPTIONS_MAP[option]
        new_data = self.coordinator.config_entry.data.copy()
        selects = dict(new_data.get("selects", {}))
        selects[self._config_key] = level
        if level > 0:
            # heating and ventilation are mutually exclusive per seat
            selects[self._location.value] = 0
        new_data["selects"] = selects
        self.hass.config_entries.async_update_entry(
            self.coordinator.config_entry, data=new_data
        )
        self.async_write_ha_state()

    @property
    def current_option(self) -> str:
        """Return the saved ventilation level."""
        level = self._saved_level()
        return next(
            (k for k, v in HEATING_LEVEL_OPTIONS_MAP.items() if v == level), "Off"
        )


class SmartRearHeatedLocation(SmartHashtagEntity, SelectEntity):
    """Saved rear seat heating preference (Smart #5); applied when climate is started."""

    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: SmartHashtagDataUpdateCoordinator,
        vehicle: str,
        location: RearHeatingLocation,
    ):
        """Initialize heated rear seat entity."""
        super().__init__(coordinator)
        self._vehicle_vin = vehicle
        self._vehicle = self.coordinator.account.vehicles.get(vehicle)
        self._location = location
        name = REAR_HEATING_LOCATION_NAMES[location]
        self._attr_name = f"Smart {vehicle} Conditioning {name}"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_preconditioning_{name.lower().replace(' ', '_')}"
        self.entity_description = REAR_HEATING_DESCRIPTIONS[location]
        self._attr_options = STEERING_HEATER_OPTIONS
        if self._vehicle is None:
            self._attr_available = False

    async def async_select_option(self, option: str, **kwargs):
        """Save the preference; this does not start climate control."""
        if self._vehicle is None:
            return
        new_data = self.coordinator.config_entry.data.copy()
        selects = dict(new_data.get("selects", {}))
        selects[self._location.value] = HEATING_LEVEL_OPTIONS_MAP[option]
        new_data["selects"] = selects
        self.hass.config_entries.async_update_entry(
            self.coordinator.config_entry, data=new_data
        )
        self.async_write_ha_state()

    @property
    def current_option(self) -> str:
        """Return the saved rear seat heating level."""
        level = self.coordinator.config_entry.data.get("selects", {}).get(
            self._location.value, 0
        )
        return next(
            (k for k, v in HEATING_LEVEL_OPTIONS_MAP.items() if v == level), "Off"
        )
