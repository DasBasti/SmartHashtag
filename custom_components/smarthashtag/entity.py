"""SmartHashtagEntity class."""
from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, LOGGER
from .const import NAME
from .const import VERSION
from .coordinator import SmartHashtagDataUpdateCoordinator


class SmartHashtagEntity(CoordinatorEntity[SmartHashtagDataUpdateCoordinator]):
    """BlueprintEntity class."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(self, coordinator: SmartHashtagDataUpdateCoordinator) -> None:
        """
        Initialize a SmartHashtagEntity with device configuration from the provided coordinator.

        This constructor:
        - Calls the superclass initializer with the coordinator (passed as a keyword argument).
        - Sets the entity's unique identifier (_attr_unique_id) using the coordinator's configuration entry.
        - Constructs the device information (_attr_device_info) using a DeviceInfo instance. The device is identified by a tuple containing the domain and entry ID from the coordinator’s configuration, and is further described by preset attributes such as name, model, and manufacturer.
        - Logs an error if accessing the coordinator's configuration fails.

        Parameters:
            coordinator (SmartHashtagDataUpdateCoordinator): The data update coordinator providing configuration details and update data for the entity.

        Note:
            Any exceptions encountered during configuration access are caught and logged; they are not re-raised.
        """
        super().__init__(coordinator=coordinator)
        try:
            self._attr_unique_id = coordinator.config_entry.entry_id
            self._attr_device_info = DeviceInfo(
                identifiers={
                    (
                        coordinator.config_entry.domain,
                        coordinator.config_entry.entry_id,
                    ),
                },
                name=NAME,
                model=VERSION,
                manufacturer=NAME,
            )
        except Exception as e:
            LOGGER.error(f"Cannot access coordinator config: {e}")
