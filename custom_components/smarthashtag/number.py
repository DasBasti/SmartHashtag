"""Support for Smart numbers."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.util import dt as dt_util

from .const import (
    CONF_VEHICLE,
    FAST_INTERVAL,
    LOGGER,
    PENDING_STATE_TIMEOUT,
)
from .coordinator import SmartHashtagDataUpdateCoordinator
from .entity import SmartHashtagEntity

if TYPE_CHECKING:
    from . import SmartHashtagConfigEntry


async def async_setup_entry(
    hass: HomeAssistant, entry: SmartHashtagConfigEntry, async_add_entities
):
    """Set up Smart number entities from a config entry."""
    coordinator = entry.runtime_data
    vehicle = coordinator.config_entry.data.get(CONF_VEHICLE)

    vehicles = coordinator.account.vehicles or {}
    if vehicle not in vehicles:
        LOGGER.error("Vehicle %s not available; skipping number setup", vehicle)
        return

    # Requires a pysmarthashtag release that provides ChargingControl.set_charging_limit
    charging_control = getattr(vehicles[vehicle], "charging_control", None)
    if not hasattr(charging_control, "set_charging_limit"):
        LOGGER.warning(
            "Installed pysmarthashtag does not support setting the charging limit; "
            "skipping charging limit"
        )
        return

    async_add_entities(
        [SmartChargingLimitNumber(coordinator, vehicle)], update_before_add=True
    )


class SmartChargingLimitNumber(SmartHashtagEntity, NumberEntity):
    """
    Number entity for the charging limit (target state of charge).

    The value follows the vehicle's reported `charging_target_soc`. Setting it
    sends the new limit through `ChargingControl.set_charging_limit`. The
    vehicle takes a while to report the new limit, so the requested value is
    shown until the vehicle confirms it or `PENDING_STATE_TIMEOUT` expires;
    meanwhile the coordinator polls fast.
    """

    _attr_translation_key = "charging_limit"
    _attr_icon = "mdi:battery-charging-high"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(
        self,
        coordinator: SmartHashtagDataUpdateCoordinator,
        vehicle: str,
    ) -> None:
        """Initialize the Charging Limit class."""
        super().__init__(coordinator)
        self._vehicle_vin = vehicle
        self._pending_value: int | None = None
        self._pending_until = None
        self._vehicle = self.coordinator.account.vehicles.get(vehicle)
        if self._vehicle is None:
            LOGGER.error("Vehicle %s not available for charging limit", vehicle)
            self._attr_available = False
            return
        self._attr_unique_id = f"{self._attr_unique_id}_charging_limit"
        control = self._vehicle.charging_control
        self._attr_native_min_value = control.CHARGING_LIMIT_MIN
        self._attr_native_max_value = control.CHARGING_LIMIT_MAX
        self._attr_native_step = control.CHARGING_LIMIT_STEP

    @property
    def _reported_value(self) -> int | None:
        """Return the charging limit reported by the vehicle."""
        if self._vehicle is None or self._vehicle.battery is None:
            return None
        target = self._vehicle.battery.charging_target_soc
        if target is None or target.value is None:
            return None
        return int(target.value)

    @property
    def native_value(self) -> float | None:
        """Return the charging limit in percent."""
        if self._pending_value is not None:
            return self._pending_value
        return self._reported_value

    def _clear_pending_state(self) -> None:
        self._pending_value = None
        self._pending_until = None
        self.coordinator.reset_update_interval("charging_limit")

    @callback
    def _handle_coordinator_update(self) -> None:
        """Drop the requested value once the vehicle confirms it or it times out."""
        if self._pending_value is not None and (
            self._reported_value == self._pending_value
            or dt_util.utcnow() >= self._pending_until
        ):
            self._clear_pending_state()
        super()._handle_coordinator_update()

    async def async_set_native_value(self, value: float) -> None:
        """Set the charging limit."""
        if self._vehicle is None:
            raise HomeAssistantError(f"Vehicle {self._vehicle_vin} is unavailable")
        percent = int(value)
        LOGGER.debug(
            "Setting charging limit to %d%% for vehicle %s", percent, self._vehicle.vin
        )
        try:
            success = await self._vehicle.charging_control.set_charging_limit(percent)
        except Exception as err:
            raise HomeAssistantError(
                f"Failed to set the charging limit of vehicle {self._vehicle.vin}: {err}"
            ) from err

        if not success:
            raise HomeAssistantError(
                f"Vehicle {self._vehicle.vin} did not accept the charging limit"
            )

        # Show the requested value until the vehicle reports it
        self._pending_value = percent
        self._pending_until = dt_util.utcnow() + timedelta(
            seconds=PENDING_STATE_TIMEOUT
        )
        self.coordinator.set_update_interval(
            "charging_limit", timedelta(seconds=FAST_INTERVAL)
        )
        self.async_write_ha_state()

        await self.coordinator.async_request_refresh()
