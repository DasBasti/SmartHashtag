"""Support for Smart #1 / #3 switches."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .const import (
    CONF_VEHICLE,
    FAST_INTERVAL,
    LOGGER,
)
from .coordinator import SmartHashtagDataUpdateCoordinator
from .entity import SmartHashtagEntity

if TYPE_CHECKING:
    from . import SmartHashtagConfigEntry


async def async_setup_entry(
    hass: HomeAssistant, entry: SmartHashtagConfigEntry, async_add_entities
):
    """Set up Smart switch entities from a config entry."""
    coordinator = entry.runtime_data
    vehicle = coordinator.config_entry.data.get(CONF_VEHICLE)
    entities = []

    vehicles = coordinator.account.vehicles or {}
    if vehicle not in vehicles:
        LOGGER.error("Vehicle %s not available; skipping switch setup", vehicle)
        return

    entities.append(SmartChargingSwitch(coordinator, vehicle))

    async_add_entities(entities, update_before_add=True)


class SmartChargingSwitch(SmartHashtagEntity, SwitchEntity):
    """
    Switch entity for controlling and monitoring the charging state of a Smart #1/#3 vehicle.

    This switch reflects whether the vehicle is currently charging by monitoring the
    `charging_status` attribute of the vehicle's battery. It considers the switch "on"
    when `charging_status` is either "charging" or "dc_charging".

    Turning the switch on or off will start or stop charging, respectively, by invoking
    the vehicle API via the `ChargingControl` interface.

    After a charging state change (on/off), the switch triggers a fast polling interval
    (using `FAST_INTERVAL`) to quickly update the entity's state in Home Assistant.
    Once the charging state stabilizes (i.e., no further change detected), the polling
    interval is reset to normal to reduce API calls.
    """

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:ev-station"

    @property
    def translation_key(self):
        return "charging_control"

    @property
    def is_on(self) -> bool:
        """Return true if charging is active."""
        if self._vehicle is None:
            return False
        try:
            return bool(
                self._vehicle.battery
                and self._vehicle.battery.charging_status
                and self._vehicle.battery.charging_status.upper()
                in ["CHARGING", "DC_CHARGING"]
            )
        except Exception as e:
            LOGGER.warning(
                "Error accessing charging status for vehicle %s: %s",
                getattr(self._vehicle, "vin", "unknown"),
                e,
            )

    def __init__(
        self,
        coordinator: SmartHashtagDataUpdateCoordinator,
        vehicle: str,
    ) -> None:
        """Initialize the Charging Switch class."""
        super().__init__(coordinator)
        self._vehicle_vin = vehicle
        self._vehicle = self.coordinator.account.vehicles.get(vehicle)
        if self._vehicle is None:
            LOGGER.error("Vehicle %s not available for charging switch", vehicle)
            self._attr_available = False
            return
        self._attr_unique_id = f"{self._attr_unique_id}_charging_switch"
        self._last_state: bool | None = None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start charging the vehicle."""
        if self._vehicle is None:
            LOGGER.warning(
                "Cannot start charging; vehicle %s unavailable", self._vehicle_vin
            )
            return
        LOGGER.debug("Starting charging for vehicle %s", self._vehicle.vin)
        try:
            await self._vehicle.charging_control.start_charging()
            # Set fast polling to quickly reflect state changes
            self.coordinator.set_update_interval(
                "charging_switch", timedelta(seconds=FAST_INTERVAL)
            )
        except Exception:
            # Log with exception info to avoid formatting errors and aid debugging
            LOGGER.exception(
                "Error turning on charging for vehicle %s",
                getattr(self._vehicle, "vin", "unknown"),
            )

        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop charging the vehicle."""
        if self._vehicle is None:
            LOGGER.warning(
                "Cannot stop charging; vehicle %s unavailable", self._vehicle_vin
            )
            return
        LOGGER.debug("Stopping charging for vehicle %s", self._vehicle.vin)
        try:
            await self._vehicle.charging_control.stop_charging()
            # Set fast polling to quickly reflect state changes
            self.coordinator.set_update_interval(
                "charging_switch", timedelta(seconds=FAST_INTERVAL)
            )
        except Exception:
            LOGGER.exception(
                "Error turning off charging for vehicle %s",
                getattr(self._vehicle, "vin", "unknown"),
            )

        await self.coordinator.async_request_refresh()

    async def async_update(self) -> None:
        """Update the entity state and reset polling interval when stable."""
        current_state = self.is_on
        # Reset to normal interval when state has stabilized
        if self._last_state is not None and current_state == self._last_state:
            self.coordinator.reset_update_interval("charging_switch")
        self._last_state = current_state
