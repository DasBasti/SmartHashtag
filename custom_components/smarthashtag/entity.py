"""SmartHashtagEntity class."""
from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION
from .const import DOMAIN
from .const import NAME
from .const import VERSION
from .coordinator import SmartHashtagDataUpdateCoordinator


class SmartHashtagEntity(CoordinatorEntity):
    """BlueprintEntity class."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(self, coordinator: SmartHashtagDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = coordinator.config_entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            name=NAME,
            model=VERSION,
            manufacturer=NAME,
        )
