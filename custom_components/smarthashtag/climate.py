"""Support for Smart #1 / #3 switches."""

from functools import cached_property
from typing import Any
from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.climate.const import HVACMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature

from .coordinator import SmartHashtagDataUpdateCoordinator

from .const import (
    CONF_CONDITIONING_TEMP,
    CONF_VEHICLE,
    DEFAULT_CONDITIONING_TEMP,
    DOMAIN,
    LOGGER,
)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up the Smart switches by config_entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    vehicle = hass.data[DOMAIN][CONF_VEHICLE]
    entities = []

    entities.append(SmartConditioningMode(coordinator, vehicle))

    async_add_entities(entities, update_before_add=True)


class SmartConditioningMode(ClimateEntity):
    """Representation of a Smart vehicle location device tracker."""

    type = "conditioning mode"
    _attr_max_temp = 30
    _attr_min_temp = 16
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_hvac_mode = HVACMode.OFF
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
    )
    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_icon = "mdi:thermostat-auto"
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(
        self,
        coordinator: SmartHashtagDataUpdateCoordinator,
        vehicle: str,
    ) -> None:
        """Initialize the Contitioner class."""
        super().__init__()
        self.coordinator = coordinator
        self._vehicle = self.coordinator.account.vehicles[vehicle]
        self._attr_name = f"Smart {vehicle} Conditioning"
        self._attr_unique_id = f"{self._attr_unique_id}_{vehicle}"
        self._temperature = self.coordinator.config_entry.options.get(
            CONF_CONDITIONING_TEMP, DEFAULT_CONDITIONING_TEMP
        )
        self._attr_target_temperature = self._temperature

    async def async_turn_on(self) -> None:
        """Turn on the climate system."""
        await self._vehicle.climate_control.set_climate_conditioning(
            self._temperature, True
        )
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self) -> None:
        """Turn off the climate system."""
        await self._vehicle.climate_control.set_climate_conditioning(
            self._temperature, False
        )
        await self.async_set_hvac_mode(HVACMode.OFF)

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
            if hvac_mode == "heat":
                await self.async_turn_on()
            else:
                await self.async_turn_off()
        self.async_write_ha_state()

    @cached_property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        LOGGER.warning(self._vehicle.climate.interior_temperature.value)
        if self._vehicle.climate.interior_temperature.value is not None:
            return self._vehicle.climate.interior_temperature.value
        else:
            return self._attr_current_temperature.value

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
