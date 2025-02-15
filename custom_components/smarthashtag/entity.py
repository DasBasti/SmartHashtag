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
        """Initialize."""
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
