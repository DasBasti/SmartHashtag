"""Support for Smart #1 / #3 switches."""

from datetime import timedelta
from typing import Any

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.climate.const import HVACMode
from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .const import (
    CONF_CONDITIONING_TEMP,
    CONF_VEHICLE,
    DEFAULT_CONDITIONING_TEMP,
    FAST_INTERVAL,
    LOGGER,
)
from .coordinator import SmartHashtagDataUpdateCoordinator


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

    entities.append(SmartConditioningMode(coordinator, vehicle))

    async_add_entities(entities, update_before_add=True)


class SmartConditioningMode(ClimateEntity):
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
    _attr_has_entity_name = True
    _attr_icon = "mdi:thermostat-auto"
    _enable_turn_on_off_backwards_compatibility = False
    _last_mode = HVACMode.OFF

    @property
    def translation_key(self):
        return "car_climate"

    @property
    def hvac_mode(self) -> HVACMode:
        """Return hvac operating mode: heat, cool"""
        current_mode = (
            HVACMode.HEAT_COOL
            if self._vehicle.climate.pre_climate_active
            else HVACMode.OFF
        )

        # value is true, last setting is off -> keep on requesting
        if current_mode == self._last_mode:
            self.coordinator.reset_update_interval("climate")

        return current_mode

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
        """
        Initializes the SmartConditioningMode climate entity for a specific vehicle.

        Associates the entity with the provided data update coordinator and vehicle identifier, sets the entity's name and unique ID, and initializes the target temperature from configuration options.
        """
        super().__init__()
        self.coordinator = coordinator
        self._vehicle = self.coordinator.account.vehicles[vehicle]
        self._attr_name = f"Smart {vehicle} Conditioning"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_climate"
        try:
            self._temperature = self.coordinator.config_entry.options.get(
                CONF_CONDITIONING_TEMP, DEFAULT_CONDITIONING_TEMP
            )
            self._attr_target_temperature = self._temperature
        except Exception as e:
            LOGGER.error(f"Cannot access coordinator config: {e}")

    async def async_turn_on(self) -> None:
        """Turn on the climate system."""
        await self._vehicle.climate_control.set_climate_conditioning(
            self._temperature, True
        )
        self._last_mode = HVACMode.HEAT_COOL
        self.coordinator.set_update_interval(
            "climate", timedelta(seconds=FAST_INTERVAL)
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        """Turn off the climate system."""
        await self._vehicle.climate_control.set_climate_conditioning(
            self._temperature, False
        )
        self._last_mode = HVACMode.OFF
        self.coordinator.set_update_interval(
            "climate", timedelta(seconds=FAST_INTERVAL)
        )
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
