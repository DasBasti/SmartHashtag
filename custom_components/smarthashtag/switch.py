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
    """
    Initialize and set up the Smart switch entities from the provided configuration entry.

    This asynchronous function extracts the coordinator from the entry's runtime data, retrieves the vehicle
    information using the CONF_VEHICLE key from the coordinator's configuration, creates an instance of
    SmartChargingSwitch using this data, and adds the created entity to Home Assistant via the async_add_entities
    callback with an option to update the entity before it is added.

    Parameters:
        hass (HomeAssistant): The Home Assistant instance.
        entry (SmartHashtagConfigEntry): The configuration entry containing runtime and configuration data.
        async_add_entities (Callable): Callback function to add entities to Home Assistant. Entities added will be updated
            before being integrated.

    Returns:
        None
    """
    coordinator = entry.runtime_data
    vehicle = coordinator.config_entry.data.get(CONF_VEHICLE)
    entities = []

    entities.append(SmartChargingSwitch(coordinator, vehicle))

    async_add_entities(entities, update_before_add=True)


class SmartChargingSwitch(SmartHashtagEntity, SwitchEntity):
    """Representation of the Smart car charging control switch."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:ev-station"

    @property
    def translation_key(self):
        return "charging_control"

    @property
    def is_on(self) -> bool:
        """Return true if charging is active."""
        return bool(
            self._vehicle.battery
            and self._vehicle.battery.charging_status
            and self._vehicle.battery.charging_status in ["charging", "dc_charging"]
        )

    def __init__(
        self,
        coordinator: SmartHashtagDataUpdateCoordinator,
        vehicle: str,
    ) -> None:
        """Initialize the Charging Switch class."""
        super().__init__(coordinator)
        self._vehicle = self.coordinator.account.vehicles[vehicle]
        self._attr_unique_id = f"{self._attr_unique_id}_charging_switch"
        self._last_state: bool | None = None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start charging the vehicle."""
        LOGGER.debug("Starting charging for vehicle %s", self._vehicle.vin)
        await self._vehicle.charging_control.start_charging()
        # Set fast polling to quickly reflect state changes
        self.coordinator.set_update_interval(
            "charging_switch", timedelta(seconds=FAST_INTERVAL)
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop charging the vehicle."""
        LOGGER.debug("Stopping charging for vehicle %s", self._vehicle.vin)
        await self._vehicle.charging_control.stop_charging()
        # Set fast polling to quickly reflect state changes
        self.coordinator.set_update_interval(
            "charging_switch", timedelta(seconds=FAST_INTERVAL)
        )
        await self.coordinator.async_request_refresh()

    async def async_update(self) -> None:
        """Update the entity state and reset polling interval when stable."""
        current_state = self.is_on
        # Reset to normal interval when state has stabilized
        if self._last_state is not None and current_state == self._last_state:
            self.coordinator.reset_update_interval("charging_switch")
        self._last_state = current_state
