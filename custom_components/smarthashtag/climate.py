"""Support for Smart #1 / #3 switches."""

from datetime import timedelta
from typing import Any

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.climate.const import HVACMode
from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.util import dt as dt_util
from pysmarthashtag.control.climate import (
    HeatingLocation,
    RearHeatingLocation,
    VentilationLocation,
)

from .const import (
    CONF_CONDITIONING_TEMP,
    CONF_VEHICLE,
    DEFAULT_CONDITIONING_TEMP,
    FAST_INTERVAL,
    LOGGER,
    PENDING_STATE_TIMEOUT,
)
from .coordinator import SmartHashtagDataUpdateCoordinator
from .entity import SmartHashtagEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: SmartHashtagDataUpdateCoordinator, async_add_entities
):
    """
    Initialize and set up the Smart switches entities from the provided configuration entry.

    This asynchronous function extracts the coordinator from the entry's runtime data, retrieves the vehicle
    information using the CONF_VEHICLE key from the coordinator's configuration, creates an instance of
    SmartConditioningMode using this data, and adds the created entity to Home Assistant via the async_add_entities
    callback with an option to update the entity before it is added.

    Parameters:
        hass (HomeAssistant): The Home Assistant instance.
        entry (SmartHashtagDataUpdateCoordinator): The coordinator instance containing runtime and configuration data.
        async_add_entities (Callable): Callback function to add entities to Home Assistant. Entities added will be updated
            before being integrated.

    Returns:
        None
    """
    coordinator = entry.runtime_data
    vehicle = coordinator.config_entry.data.get(CONF_VEHICLE)
    entities = []

    vehicles = coordinator.account.vehicles or {}
    if vehicle not in vehicles:
        LOGGER.error("Vehicle %s not available; skipping climate setup", vehicle)
        return

    entities.append(SmartConditioningMode(coordinator, vehicle))

    async_add_entities(entities, update_before_add=True)


class SmartConditioningMode(SmartHashtagEntity, ClimateEntity):
    """Representation of the Smart car climate."""

    type = "conditioning mode"
    _attr_max_temp = 30
    _attr_min_temp = 16
    _attr_hvac_modes = [HVACMode.HEAT_COOL, HVACMode.OFF]
    _attr_hvac_mode = HVACMode.OFF
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
    )
    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = False
    _attr_icon = "mdi:thermostat-auto"
    _enable_turn_on_off_backwards_compatibility = False
    _pending_mode: HVACMode | None = None
    _pending_until = None

    @property
    def translation_key(self):
        return "car_climate"

    @property
    def _reported_mode(self) -> HVACMode | None:
        """Return the conditioning mode reported by the vehicle, None if unknown.

        An unknown mode never confirms a pending command.
        """
        climate = None if self._vehicle is None else self._vehicle.climate
        if climate is None or climate.pre_climate_active is None:
            return None
        if climate.pre_climate_active:
            return HVACMode.HEAT_COOL
        return HVACMode.OFF

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return the requested mode while pending, else the reported mode."""
        if self._pending_mode is not None:
            return self._pending_mode
        return self._reported_mode

    def _clear_pending_mode(self) -> None:
        self._pending_mode = None
        self._pending_until = None
        self.coordinator.reset_update_interval("climate")

    @callback
    def _handle_coordinator_update(self) -> None:
        """Drop the requested mode once the vehicle confirms it or it times out.

        Fast polling ends with it, also when the vehicle never confirms the
        command or ends the preconditioning on its own later.
        """
        if self._pending_mode is not None and (
            self._reported_mode == self._pending_mode
            or dt_util.utcnow() >= self._pending_until
        ):
            self._clear_pending_mode()
        super()._handle_coordinator_update()

    @property
    def temperature_unit(self):
        return UnitOfTemperature.CELSIUS

    @property
    def max_temp(self):
        """Return max temperature."""
        return 30

    @property
    def min_temp(self):
        """Return min temperature."""
        return 16

    @property
    def target_temperature(self):
        """Return target temperature."""
        return self._temperature

    def __init__(
        self,
        coordinator: SmartHashtagDataUpdateCoordinator,
        vehicle: str,
    ) -> None:
        """Initialize the Contitioner class."""
        super().__init__(coordinator)
        self._vehicle_vin = vehicle
        self._vehicle = self.coordinator.account.vehicles.get(vehicle)
        if self._vehicle is None:
            LOGGER.error("Vehicle %s not available for climate control", vehicle)
            self._attr_available = False

        self._attr_name = f"Smart {vehicle} Conditioning"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_climate"
        try:
            self._temperature = self.coordinator.config_entry.options.get(
                CONF_CONDITIONING_TEMP, DEFAULT_CONDITIONING_TEMP
            )
            self._attr_target_temperature = self._temperature
        except Exception as e:
            LOGGER.error(f"Cannot access coordinator config: {e}")

    def _restore_heating_levels(self) -> None:
        """Restore heating levels from saved config entry data to the climate control."""
        selects = self.coordinator.config_entry.data.get("selects", {})
        for location in HeatingLocation:
            level = selects.get(location.value, 0)
            try:
                self._vehicle.climate_control.set_heating_level(location, level)
            except Exception as e:
                LOGGER.warning(
                    "Failed to restore heating level for %s: %s", location, e
                )

    def _restore_ventilation_levels(self) -> None:
        """Restore saved seat ventilation and rear heating levels (Smart #5 only)."""
        if not getattr(self._vehicle.climate_control, "use_zaf", False):
            return
        selects = self.coordinator.config_entry.data.get("selects", {})
        for location in VentilationLocation:
            level = selects.get(f"ventilation-{location.value}", 0)
            try:
                self._vehicle.climate_control.set_ventilation_level(location, level)
            except Exception as e:
                LOGGER.warning(
                    "Failed to restore ventilation level for %s: %s", location, e
                )
        for r_location in RearHeatingLocation:
            level = selects.get(r_location.value, 0)
            try:
                self._vehicle.climate_control.set_rear_heating_level(r_location, level)
            except Exception as e:
                LOGGER.warning(
                    "Failed to restore rear heating level for %s: %s", r_location, e
                )

    async def async_turn_on(self) -> None:
        """Turn on the climate system."""
        if self._vehicle is None:
            LOGGER.warning(
                "Cannot turn on climate; vehicle %s unavailable", self._vehicle_vin
            )
            return
        await self.coordinator.account.select_active_vehicle(self._vehicle_vin)
        self._restore_heating_levels()
        self._restore_ventilation_levels()
        await self._set_conditioning(HVACMode.HEAT_COOL)

    async def async_turn_off(self) -> None:
        """Turn off the climate system."""
        if self._vehicle is None:
            LOGGER.warning(
                "Cannot turn off climate; vehicle %s unavailable", self._vehicle_vin
            )
            return
        await self._set_conditioning(HVACMode.OFF)

    async def _set_conditioning(self, mode: HVACMode) -> None:
        """Send the conditioning command and poll fast until the vehicle confirms."""
        active = mode == HVACMode.HEAT_COOL
        success = await self._vehicle.climate_control.set_climate_conditioning(
            self._temperature, active
        )
        if not success:
            self._clear_pending_mode()
            self.async_write_ha_state()
            raise HomeAssistantError(
                f"Vehicle {self._vehicle_vin} did not accept the climate command"
            )

        # Show the requested mode until the vehicle reports it
        self._pending_mode = mode
        self._pending_until = dt_util.utcnow() + timedelta(
            seconds=PENDING_STATE_TIMEOUT
        )
        self.coordinator.set_update_interval(
            "climate", timedelta(seconds=FAST_INTERVAL)
        )
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature for the vehicle."""
        temperature = kwargs[ATTR_TEMPERATURE]
        if temperature is not None:
            self._temperature = temperature
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        if hvac_mode is not None:
            self._attr_hvac_mode = hvac_mode
            if hvac_mode == HVACMode.HEAT_COOL:
                await self.async_turn_on()
            else:
                await self.async_turn_off()
        self.async_write_ha_state()

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        if self._vehicle is None or self._vehicle.climate is None:
            return None
        return self._vehicle.climate.interior_temperature.value

    def set_fan_mode(self, fan_mode: str) -> None:
        """Set the fan mode."""
        raise NotImplementedError

    def set_humidity(self, humidity: float) -> None:
        """Set the humidity level."""
        raise NotImplementedError

    def set_hvac_mode(self, hvac_mode: str) -> None:
        """Set the HVAC mode."""
        raise NotImplementedError

    def set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode."""
        raise NotImplementedError

    def set_swing_mode(self, swing_mode: str) -> None:
        """Set the swing mode."""
        raise NotImplementedError

    def set_temperature(self, **kwargs: Any) -> None:
        """Set the target temperature."""
        raise NotImplementedError

    def turn_aux_heat_off(self) -> None:
        """Turn off the auxiliary heat."""
        raise NotImplementedError

    def turn_aux_heat_on(self) -> None:
        """Turn on the auxiliary heat."""
        raise NotImplementedError

    def turn_off(self) -> None:
        """Turn off the climate system."""
        raise NotImplementedError

    def turn_on(self) -> None:
        """Turn on the climate system."""
        raise NotImplementedError
