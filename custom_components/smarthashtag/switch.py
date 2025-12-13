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
        entry (SmartHashtagDataUpdateCoordinator): The coordinator instance containing runtime and configuration data.
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


class SmartChargingSwitch(SwitchEntity):
    """Representation of the Smart car charging control switch."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True
    _attr_icon = "mdi:ev-station"
    _last_state = False

    @property
    def translation_key(self):
        return "charging_control"

    @property
    def is_on(self) -> bool:
        """Return true if charging is active."""
        is_charging = (
            self._vehicle.battery
            and self._vehicle.battery.charging_status
            and self._vehicle.battery.charging_status in ["charging", "dc_charging"]
        )

        # If state changed, reset update interval
        if is_charging != self._last_state:
            self.coordinator.reset_update_interval("charging_switch")

        return is_charging

    def __init__(
        self,
        coordinator: SmartHashtagDataUpdateCoordinator,
        vehicle: str,
    ) -> None:
        """Initialize the Charging Switch class."""
        super().__init__()
        self.coordinator = coordinator
        self._vehicle = self.coordinator.account.vehicles[vehicle]
        self._attr_name = f"Smart {vehicle} Charging"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_charging_switch"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start charging the vehicle."""
        LOGGER.debug("Starting charging for vehicle %s", self._vehicle.vin)
        await self._vehicle.charging_control.start_charging()
        self._last_state = True
        self.coordinator.set_update_interval(
            "charging_switch", timedelta(seconds=FAST_INTERVAL)
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop charging the vehicle."""
        LOGGER.debug("Stopping charging for vehicle %s", self._vehicle.vin)
        await self._vehicle.charging_control.stop_charging()
        self._last_state = False
        self.coordinator.set_update_interval(
            "charging_switch", timedelta(seconds=FAST_INTERVAL)
        )
        await self.coordinator.async_request_refresh()
