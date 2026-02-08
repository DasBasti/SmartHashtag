"""Sensor platform for Smar #1/#3 intergration."""

from __future__ import annotations

import dataclasses
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from pysmarthashtag.models import ValueWithUnit

from .const import (
    CONF_CHARGING_INTERVAL,
    CONF_DRIVING_INTERVAL,
    CONF_VEHICLE,
    DEFAULT_CHARGING_INTERVAL,
    DEFAULT_DRIVING_INTERVAL,
    LOGGER,
)
from .coordinator import SmartHashtagDataUpdateCoordinator
from .entity import SmartHashtagEntity
from .sensor_groups import (
    ENTITY_BATTERY_DESCRIPTIONS,
    ENTITY_CLIMATE_DESCRIPTIONS,
    ENTITY_GENERAL_DESCRIPTIONS,
    ENTITY_MAINTENANCE_DESCRIPTIONS,
    ENTITY_RUNNING_DESCRIPTIONS,
    ENTITY_SAFETY_DESCRIPTIONS,
    ENTITY_TIRE_DESCRIPTIONS,
)


def remove_vin_from_key(key: str) -> str:
    """Remove the vin from the key."""
    return "_".join(key.split("_")[1:])


def vin_from_key(key: str) -> str:
    """Get the vin from the key."""
    return key.split("_")[0]


async def async_setup_entry(hass, entry, async_add_devices):
    """
    Initialize the Smart Hashtag sensor platform for Home Assistant.

    This asynchronous function sets up and registers sensor devices for a Smart Hashtag vehicle by iterating over
    multiple predefined sensor entity descriptions. It retrieves the coordinator from the configuration entry’s runtime data,
    extracts the vehicle identifier from the coordinator’s configuration, and creates sensor instances with updated entity
    descriptions that incorporate the vehicle identifier. The sensors added include battery range, tire, general update,
    maintenance, running, climate, and safety sensors.

    Parameters:
        hass (HomeAssistant): The Home Assistant instance.
        entry (ConfigEntry): The configuration entry that provides integration-specific data, including runtime data and
            the vehicle configuration.
        async_add_devices (Callable[[Iterable[SensorEntity]], None]): A callback function used to add the sensor entities
            to Home Assistant.

    Returns:
        None

    Example:
        await async_setup_entry(hass, entry, async_add_devices)
    """
    coordinator = entry.runtime_data
    vehicle = coordinator.config_entry.data.get(CONF_VEHICLE)

    async_add_devices(
        SmartHashtagBatteryRangeSensor(
            coordinator=coordinator,
            entity_description=dataclasses.replace(
                entity_description, key=f"{vehicle}_{entity_description.key}"
            ),
        )
        for entity_description in ENTITY_BATTERY_DESCRIPTIONS
    )

    async_add_devices(
        SmartHashtagTireSensor(
            coordinator=coordinator,
            entity_description=dataclasses.replace(
                entity_description, key=f"{vehicle}_{entity_description.key}"
            ),
        )
        for entity_description in ENTITY_TIRE_DESCRIPTIONS
    )

    async_add_devices(
        SmartHashtagUpdateSensor(
            coordinator=coordinator,
            entity_description=dataclasses.replace(
                entity_description, key=f"{vehicle}_{entity_description.key}"
            ),
        )
        for entity_description in ENTITY_GENERAL_DESCRIPTIONS
    )

    async_add_devices(
        SmartHashtagMaintenanceSensor(
            coordinator=coordinator,
            entity_description=dataclasses.replace(
                entity_description, key=f"{vehicle}_{entity_description.key}"
            ),
        )
        for entity_description in ENTITY_MAINTENANCE_DESCRIPTIONS
    )

    async_add_devices(
        SmartHashtagRunningSensor(
            coordinator=coordinator,
            entity_description=dataclasses.replace(
                entity_description, key=f"{vehicle}_{entity_description.key}"
            ),
        )
        for entity_description in ENTITY_RUNNING_DESCRIPTIONS
    )

    async_add_devices(
        SmartHashtagClimateSensor(
            coordinator=coordinator,
            entity_description=dataclasses.replace(
                entity_description, key=f"{vehicle}_{entity_description.key}"
            ),
        )
        for entity_description in ENTITY_CLIMATE_DESCRIPTIONS
    )

    async_add_devices(
        SmartHashtagSafetySensor(
            coordinator=coordinator,
            entity_description=dataclasses.replace(
                entity_description, key=f"{vehicle}_{entity_description.key}"
            ),
        )
        for entity_description in ENTITY_SAFETY_DESCRIPTIONS
    )


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
        self._last_valid_value = None

    @property
    def native_value(self) -> int:
        """Return the native value of the sensor."""
        try:
            vehicle = self.coordinator.account.vehicles.get(
                vin_from_key(self.entity_description.key)
            )
            if vehicle is None or vehicle.battery is None:
                return self._last_valid_value

            data = getattr(
                vehicle.battery,
                remove_vin_from_key(self.entity_description.key),
            )

            if "charging_current" in self.entity_description.key:
                if data.value != 0:
                    self.coordinator.set_update_interval(
                        "charging",
                        timedelta(
                            seconds=self.coordinator.config_entry.options.get(
                                CONF_CHARGING_INTERVAL, DEFAULT_CHARGING_INTERVAL
                            )
                        ),
                    )
                    self.hass.async_create_task(
                        self.coordinator.async_request_refresh()
                    )
                else:
                    self.coordinator.reset_update_interval("charging")

            if "charging_power" in self.entity_description.key:
                # Store valid non-zero values for future use
                if data.value is not None and data.value != 0:
                    self._last_valid_value = data.value
                # When charging is active but power reads as 0, retain last valid value
                charging_status = vehicle.battery.charging_status
                is_charging = charging_status in ("CHARGING", "DC_CHARGING")
                if is_charging and (data.value is None or data.value == 0):
                    if self._last_valid_value is not None:
                        return self._last_valid_value
                # Handle -0.0 case (return 0.0 only if not charging or no previous value)
                if data.value == -0.0:
                    return 0.0

            if "charging_status" in self.entity_description.key:
                if isinstance(data, str):
                    data = data.lower()
                    allowed = set(self.entity_description.options or {})
                    if allowed and data not in allowed:
                        LOGGER.debug(
                            "Charging status %s not in allowed options %s; reporting unknown",
                            data,
                            allowed,
                        )
                        return None
                return data

            # invert power consumption value to display the consumed power as positive
            if "average_power_consumption" in self.entity_description.key:
                if data.value:
                    return data.value * -1
                return data

            if isinstance(data, ValueWithUnit):
                return data.value

            return data

        except AttributeError as err:
            LOGGER.error(
                "AttributeError value: %s (%s)", self.entity_description.key, err
            )
            return self._last_valid_value

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement of the sensor."""
        try:
            vehicle = self.coordinator.account.vehicles.get(
                vin_from_key(self.entity_description.key)
            )
            if vehicle is None or vehicle.battery is None:
                return None

            data = getattr(
                vehicle.battery,
                remove_vin_from_key(self.entity_description.key),
            )
            if "charging_status" in self.entity_description.key:
                return None
            if "charger_connection_status" in self.entity_description.key:
                return None
            if isinstance(data, ValueWithUnit):
                return data.unit

            return data

        except AttributeError as err:
            LOGGER.debug(
                "AttributeError unit: %s (%s)", self.entity_description.key, err
            )
            return None


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
        self._last_valid_value = None

    @property
    def native_value(self) -> float:
        """Return the native value of the sensor."""
        try:
            key = "_".join(self.entity_description.key.split("_")[1:-1])
            tire_idx = int(self.entity_description.key.split("_")[-1])
            tires = self.coordinator.account.vehicles.get(
                vin_from_key(self.entity_description.key)
            ).tires

            if not tires:
                return self._last_valid_value

            value = getattr(tires, key)[tire_idx].value
            self._last_valid_value = value
            return value

        except (AttributeError, IndexError, TypeError) as err:
            LOGGER.debug(
                "Tire value unavailable for %s: %s", self.entity_description.key, err
            )
            return self._last_valid_value

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement of the sensor."""
        try:
            key = "_".join(self.entity_description.key.split("_")[1:-1])
            tire_idx = int(self.entity_description.key.split("_")[-1])
            tires = self.coordinator.account.vehicles.get(
                vin_from_key(self.entity_description.key)
            ).tires

            if not tires:
                return None

            data = getattr(tires, key)[tire_idx]

        except (AttributeError, IndexError, TypeError) as err:
            LOGGER.debug(
                "Tire unit unavailable for %s: %s", self.entity_description.key, err
            )
            return None

        # FIXME: if pysmarthashtag is updated to return the unit as °C remove this
        if data.unit == "C":
            return "°C"

        return data.unit


class SmartHashtagUpdateSensor(SmartHashtagEntity, SensorEntity):
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
        self._last_valid_value = None

    @property
    def native_value(self) -> float:
        """Return the native value of the sensor."""
        try:
            key = remove_vin_from_key(self.entity_description.key)
            vin = vin_from_key(self.entity_description.key)
            vehicle = self.coordinator.account.vehicles.get(vin)
            if vehicle is None:
                return self._last_valid_value

            if key.startswith("service"):
                key = self.entity_description.key.split("_")[-1]
                if vehicle.service is None:
                    return self._last_valid_value
                data = vehicle.service[key]
            else:
                data = getattr(
                    vehicle, remove_vin_from_key(self.entity_description.key)
                )

            if key == "engine_state":
                if data == "engine_running":
                    self.coordinator.set_update_interval(
                        "driving",
                        timedelta(
                            seconds=self.coordinator.config_entry.options.get(
                                CONF_DRIVING_INTERVAL, DEFAULT_DRIVING_INTERVAL
                            )
                        ),
                    )
                    self.hass.async_create_task(
                        self.coordinator.async_request_refresh()
                    )
                    self.icon = "mdi:engine"
                else:
                    self.coordinator.reset_update_interval("driving")
                    self.icon = "mdi:engine-off"

            if isinstance(data, ValueWithUnit):
                return data.value
            return data

        except AttributeError as err:
            LOGGER.error(
                "AttributeError value: %s (%s)", self.entity_description.key, err
            )
            return self._last_valid_value

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement of the sensor."""
        try:
            key = remove_vin_from_key(self.entity_description.key)
            vin = vin_from_key(self.entity_description.key)
            vehicle = self.coordinator.account.vehicles.get(vin)
            if vehicle is None:
                return self.entity_description.native_unit_of_measurement
            if key.startswith("service"):
                key = key.rsplit("_", maxsplit=1)[-1]
                if vehicle.service is None:
                    return self.entity_description.native_unit_of_measurement
                data = vehicle.service[key]
            else:
                data = getattr(vehicle, key)
            if isinstance(data, ValueWithUnit):
                return data.unit
        except AttributeError as err:
            LOGGER.debug(
                "AttributeError in native_unit_of_measurement: %s (%s)",
                self.entity_description.key,
                err,
            )
        return self.entity_description.native_unit_of_measurement


class SmartHashtagMaintenanceSensor(SmartHashtagEntity, SensorEntity):
    """Tire Status class."""

    def __init__(
        self,
        coordinator: SmartHashtagDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """
        Initialize the maintenance sensor instance with vehicle data and a unique identifier.

        This constructor extracts the maintenance data for a specific vehicle by using the coordinator's account data.
        It retrieves the vehicle's maintenance information by extracting the VIN from the provided entity description key
        and accessing the corresponding vehicle object. The sensor's unique identifier is then updated by appending the
        entity description key to ensure its distinctiveness.

        Parameters:
            coordinator (SmartHashtagDataUpdateCoordinator): The coordinator that manages data updates and provides access
                to the account's vehicles.
            entity_description (SensorEntityDescription): The sensor's metadata containing the key used to extract the VIN
                and retrieve related maintenance data.

        Returns:
            None
        """
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._attr_unique_id}_{entity_description.key}"
        self.entity_description = entity_description
        self._last_valid_value = None

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        try:
            key = remove_vin_from_key(self.entity_description.key)
            vin = vin_from_key(self.entity_description.key)
            vehicle = self.coordinator.account.vehicles.get(vin)
            if vehicle is None or vehicle.maintenance is None:
                return self._last_valid_value

            data = getattr(vehicle.maintenance, key)
            if isinstance(data, ValueWithUnit):
                self._last_valid_value = data.value
                return data.value
            self._last_valid_value = data
            return data

        except AttributeError as err:
            LOGGER.error(
                "AttributeError value: %s (%s)", self.entity_description.key, err
            )
            return self._last_valid_value


class SmartHashtagRunningSensor(SmartHashtagEntity, SensorEntity):
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
        self._last_valid_value = None

    @property
    def native_value(self) -> float | int | str | None:
        """Return the native value of the sensor."""
        try:
            key = remove_vin_from_key(self.entity_description.key)
            vin = vin_from_key(self.entity_description.key)
            vehicle = self.coordinator.account.vehicles.get(vin)
            if vehicle is None or vehicle.running is None:
                return self._last_valid_value

            data = getattr(vehicle.running, key)
            if isinstance(data, ValueWithUnit):
                self._last_valid_value = data.value
                return data.value
            self._last_valid_value = data
            return data

        except AttributeError as err:
            LOGGER.error(
                "AttributeError value: %s (%s)", self.entity_description.key, err
            )
            return self._last_valid_value

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement of the sensor."""
        try:
            key = remove_vin_from_key(self.entity_description.key)
            vin = vin_from_key(self.entity_description.key)
            vehicle = self.coordinator.account.vehicles.get(vin)
            if vehicle is None or vehicle.running is None:
                return self.entity_description.native_unit_of_measurement
            data = getattr(vehicle.running, key)
            if isinstance(data, ValueWithUnit):
                return data.unit
        except AttributeError as err:
            LOGGER.debug(
                "AttributeError in native_unit_of_measurement: %s (%s)",
                self.entity_description.key,
                err,
            )
        return self.entity_description.native_unit_of_measurement


class SmartHashtagClimateSensor(SmartHashtagEntity, SensorEntity):
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
        self._last_valid_value = None

    @property
    def native_value(self) -> float | int | str | None:
        """Return the native value of the sensor."""
        try:
            key = remove_vin_from_key(self.entity_description.key)
            vin = vin_from_key(self.entity_description.key)
            vehicle = self.coordinator.account.vehicles.get(vin)
            if vehicle is None or vehicle.climate is None:
                return self._last_valid_value

            data = getattr(vehicle.climate, key)
            if isinstance(data, ValueWithUnit):
                self._last_valid_value = data.value
                return data.value
            self._last_valid_value = data
            return data

        except AttributeError as err:
            # Interior PM25 sensor is not available in all vehicle variants
            key = remove_vin_from_key(self.entity_description.key)
            if key == "interior_PM25":
                LOGGER.info(
                    "Field '%s' not found in data (not available in this vehicle variant)",
                    self.entity_description.key,
                )
            else:
                LOGGER.error(
                    "AttributeError value: %s (%s)", self.entity_description.key, err
                )
            return self._last_valid_value

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement of the sensor."""
        try:
            key = remove_vin_from_key(self.entity_description.key)
            vin = vin_from_key(self.entity_description.key)
            vehicle = self.coordinator.account.vehicles.get(vin)
            if vehicle is None or vehicle.climate is None:
                return self.entity_description.native_unit_of_measurement
            data = getattr(vehicle.climate, key)
            if isinstance(data, ValueWithUnit):
                return data.unit
        except AttributeError as err:
            LOGGER.debug(
                "AttributeError in native_unit_of_measurement: %s (%s)",
                self.entity_description.key,
                err,
            )
        return self.entity_description.native_unit_of_measurement


class SmartHashtagSafetySensor(SmartHashtagEntity, SensorEntity):
    """Safety class."""

    def __init__(
        self,
        coordinator: SmartHashtagDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._attr_unique_id}_{entity_description.key}"
        self.entity_description = entity_description
        self._last_valid_value = None

    @property
    def native_value(self) -> float | int | str | None:
        """Return the native value of the sensor."""
        try:
            key = remove_vin_from_key(self.entity_description.key)
            vin = vin_from_key(self.entity_description.key)
            vehicle = self.coordinator.account.vehicles.get(vin)
            if vehicle is None or vehicle.safety is None:
                return self._last_valid_value

            data = getattr(vehicle.safety, key)
            if isinstance(data, ValueWithUnit):
                self._last_valid_value = data.value
                return data.value
            self._last_valid_value = data
            return data

        except AttributeError as err:
            LOGGER.error(
                "AttributeError value: %s (%s)", self.entity_description.key, err
            )
            return self._last_valid_value

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement of the sensor."""
        try:
            key = remove_vin_from_key(self.entity_description.key)
            vin = vin_from_key(self.entity_description.key)
            vehicle = self.coordinator.account.vehicles.get(vin)
            if vehicle is None or vehicle.safety is None:
                return self.entity_description.native_unit_of_measurement
            data = getattr(vehicle.safety, key)
            if isinstance(data, ValueWithUnit):
                return data.unit
        except AttributeError as err:
            LOGGER.debug(
                "AttributeError in native_unit_of_measurement: %s (%s)",
                self.entity_description.key,
                err,
            )
        return self.entity_description.native_unit_of_measurement
