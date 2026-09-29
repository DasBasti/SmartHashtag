"""Support for Smart #1 / #3 door locks."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.components.lock import LockEntity
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
    """Set up Smart lock entities from a config entry."""
    coordinator = entry.runtime_data
    vehicle = coordinator.config_entry.data.get(CONF_VEHICLE)

    vehicles = coordinator.account.vehicles or {}
    if vehicle not in vehicles:
        LOGGER.error("Vehicle %s not available; skipping lock setup", vehicle)
        return

    # Requires a pysmarthashtag release that provides Vehicle.door_lock_control
    if getattr(vehicles[vehicle], "door_lock_control", None) is None:
        LOGGER.warning(
            "Installed pysmarthashtag does not support door lock control; "
            "skipping door lock"
        )
        return

    async_add_entities([SmartDoorLock(coordinator, vehicle)], update_before_add=True)


class SmartDoorLock(SmartHashtagEntity, LockEntity):
    """
    Lock entity for the central locking of a Smart vehicle.

    The state follows the vehicle's reported `central_locking_status`, where 0
    means unlocked. Locking or unlocking sends the RDL_2 / RDU_2 remote door
    service. The vehicle takes a while to report the new state, so the entity
    shows locking/unlocking until the vehicle confirms it or
    `PENDING_STATE_TIMEOUT` expires; meanwhile the coordinator polls fast.
    """

    _attr_translation_key = "door_lock"

    def __init__(
        self,
        coordinator: SmartHashtagDataUpdateCoordinator,
        vehicle: str,
    ) -> None:
        """Initialize the Door Lock class."""
        super().__init__(coordinator)
        self._vehicle_vin = vehicle
        self._pending_locked: bool | None = None
        self._pending_until = None
        self._vehicle = self.coordinator.account.vehicles.get(vehicle)
        if self._vehicle is None:
            LOGGER.error("Vehicle %s not available for door lock", vehicle)
            self._attr_available = False
            return
        self._attr_unique_id = f"{self._attr_unique_id}_door_lock"

    @property
    def is_locked(self) -> bool | None:
        """Return true if the vehicle reports the central locking as locked."""
        if self._vehicle is None or self._vehicle.safety is None:
            return None
        status = self._vehicle.safety.central_locking_status
        if status is None:
            return None
        return status != 0

    @property
    def is_locking(self) -> bool:
        """Return true while a lock command waits for the vehicle to confirm."""
        return self._pending_locked is True

    @property
    def is_unlocking(self) -> bool:
        """Return true while an unlock command waits for the vehicle to confirm."""
        return self._pending_locked is False

    def _clear_pending_state(self) -> None:
        self._pending_locked = None
        self._pending_until = None
        self.coordinator.reset_update_interval("door_lock")

    @callback
    def _handle_coordinator_update(self) -> None:
        """Drop the pending state once the vehicle confirms it or it times out."""
        if self._pending_locked is not None and (
            self.is_locked == self._pending_locked
            or dt_util.utcnow() >= self._pending_until
        ):
            self._clear_pending_state()
        super()._handle_coordinator_update()

    async def _set_locked(self, locked: bool) -> None:
        if self._vehicle is None:
            raise HomeAssistantError(f"Vehicle {self._vehicle_vin} is unavailable")
        action = "lock" if locked else "unlock"
        LOGGER.debug("Sending %s command to vehicle %s", action, self._vehicle.vin)
        lock_control = self._vehicle.door_lock_control
        try:
            if locked:
                success = await lock_control.lock()
            else:
                success = await lock_control.unlock()
        except Exception as err:
            self._clear_pending_state()
            self.async_write_ha_state()
            raise HomeAssistantError(
                f"Failed to {action} vehicle {self._vehicle.vin}: {err}"
            ) from err

        if not success:
            self._clear_pending_state()
            self.async_write_ha_state()
            raise HomeAssistantError(
                f"Vehicle {self._vehicle.vin} did not accept the {action} command"
            )

        # Show locking/unlocking until the vehicle reports the new state
        self._pending_locked = locked
        self._pending_until = dt_util.utcnow() + timedelta(
            seconds=PENDING_STATE_TIMEOUT
        )
        self.coordinator.set_update_interval(
            "door_lock", timedelta(seconds=FAST_INTERVAL)
        )
        self.async_write_ha_state()

        await self.coordinator.async_request_refresh()

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock all doors of the vehicle."""
        await self._set_locked(True)

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock all doors of the vehicle."""
        await self._set_locked(False)
