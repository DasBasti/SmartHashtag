"""Support for Smart #1 / #3 covers."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
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
    """Set up Smart cover entities from a config entry."""
    coordinator = entry.runtime_data
    vehicle = coordinator.config_entry.data.get(CONF_VEHICLE)

    vehicles = coordinator.account.vehicles or {}
    if vehicle not in vehicles:
        LOGGER.error("Vehicle %s not available; skipping cover setup", vehicle)
        return

    # Requires a pysmarthashtag release that provides DoorLockControl.open_trunk
    lock_control = getattr(vehicles[vehicle], "door_lock_control", None)
    if not hasattr(lock_control, "open_trunk"):
        return

    async_add_entities([SmartTrunk(coordinator, vehicle)], update_before_add=True)


class SmartTrunk(SmartHashtagEntity, CoverEntity):
    """
    Cover entity for the trunk of a Smart vehicle.

    The state follows the vehicle's reported `trunk_open_status`, where 1 means
    open. Opening or closing sends the RDU_2 / RDL_2 remote door service with
    the trunk as target. The vehicle takes a while to report the new state, so
    the entity shows opening/closing until the vehicle confirms it or
    `PENDING_STATE_TIMEOUT` expires; meanwhile the coordinator polls fast.
    """

    _attr_translation_key = "trunk"
    _attr_device_class = CoverDeviceClass.DOOR
    _attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE

    def __init__(
        self,
        coordinator: SmartHashtagDataUpdateCoordinator,
        vehicle: str,
    ) -> None:
        """Initialize the Trunk class."""
        super().__init__(coordinator)
        self._vehicle_vin = vehicle
        self._pending_closed: bool | None = None
        self._pending_until = None
        self._vehicle = self.coordinator.account.vehicles.get(vehicle)
        if self._vehicle is None:
            LOGGER.error("Vehicle %s not available for trunk", vehicle)
            self._attr_available = False
            return
        self._attr_unique_id = f"{self._attr_unique_id}_trunk"

    @property
    def is_closed(self) -> bool | None:
        """Return true if the vehicle reports the trunk as closed."""
        if self._vehicle is None or self._vehicle.safety is None:
            return None
        status = self._vehicle.safety.trunk_open_status
        if status is None:
            return None
        return status != 1

    @property
    def is_opening(self) -> bool:
        """Return true while an open command waits for the vehicle to confirm."""
        return self._pending_closed is False

    @property
    def is_closing(self) -> bool:
        """Return true while a close command waits for the vehicle to confirm."""
        return self._pending_closed is True

    def _clear_pending_state(self) -> None:
        self._pending_closed = None
        self._pending_until = None
        self.coordinator.reset_update_interval("trunk")

    @callback
    def _handle_coordinator_update(self) -> None:
        """Drop the pending state once the vehicle confirms it or it times out."""
        if self._pending_closed is not None and (
            self.is_closed == self._pending_closed
            or dt_util.utcnow() >= self._pending_until
        ):
            self._clear_pending_state()
        super()._handle_coordinator_update()

    async def _set_closed(self, closed: bool) -> None:
        if self._vehicle is None:
            raise HomeAssistantError(f"Vehicle {self._vehicle_vin} is unavailable")
        action = "close" if closed else "open"
        LOGGER.debug(
            "Sending trunk %s command to vehicle %s", action, self._vehicle.vin
        )
        lock_control = self._vehicle.door_lock_control
        try:
            if closed:
                success = await lock_control.close_trunk()
            else:
                success = await lock_control.open_trunk()
        except Exception as err:
            self._clear_pending_state()
            self.async_write_ha_state()
            raise HomeAssistantError(
                f"Failed to {action} the trunk of vehicle {self._vehicle.vin}: {err}"
            ) from err

        if not success:
            self._clear_pending_state()
            self.async_write_ha_state()
            raise HomeAssistantError(
                f"Vehicle {self._vehicle.vin} did not accept the trunk {action} command"
            )

        # Show opening/closing until the vehicle reports the new state
        self._pending_closed = closed
        self._pending_until = dt_util.utcnow() + timedelta(
            seconds=PENDING_STATE_TIMEOUT
        )
        self.coordinator.set_update_interval("trunk", timedelta(seconds=FAST_INTERVAL))
        self.async_write_ha_state()

        await self.coordinator.async_request_refresh()

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the trunk."""
        await self._set_closed(False)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the trunk."""
        await self._set_closed(True)
