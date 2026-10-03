"""Support for Smart #1 / #3 switches."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.util import dt as dt_util
from pysmarthashtag.control.climate import HeatingLocation

from .const import (
    CONF_VEHICLE,
    DEFAULT_SEATHEATING_LEVEL,
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
    """Set up Smart switch entities from a config entry."""
    coordinator = entry.runtime_data
    vehicle = coordinator.config_entry.data.get(CONF_VEHICLE)
    entities = []

    vehicles = coordinator.account.vehicles or {}
    if vehicle not in vehicles:
        LOGGER.error("Vehicle %s not available; skipping switch setup", vehicle)
        return

    entities.append(SmartChargingSwitch(coordinator, vehicle))

    # Requires a pysmarthashtag release that provides ClimateControll.set_defrost
    climate_control = getattr(vehicles[vehicle], "climate_control", None)
    if hasattr(climate_control, "set_defrost"):
        entities.append(SmartDefrostSwitch(coordinator, vehicle))

    # Requires a pysmarthashtag release that provides ClimateControll.set_heating
    if hasattr(climate_control, "set_heating"):
        entities.extend(
            SmartHeatingSwitch(coordinator, vehicle, description)
            for description in HEATING_SWITCH_DESCRIPTIONS
        )

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


class SmartPendingStateSwitch(SmartHashtagEntity, SwitchEntity):
    """
    Base for switches that send a remote command the vehicle confirms with a delay.

    The vehicle takes a while to report the new state, so the requested state is
    shown until the vehicle confirms it or `PENDING_STATE_TIMEOUT` expires;
    meanwhile the coordinator polls fast.
    """

    # Name of the fast polling request registered with the coordinator
    _interval_key: str
    # Human readable command name for log messages
    _command_name: str

    def __init__(
        self,
        coordinator: SmartHashtagDataUpdateCoordinator,
        vehicle: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._vehicle_vin = vehicle
        self._pending_state: bool | None = None
        self._pending_until = None
        self._vehicle = self.coordinator.account.vehicles.get(vehicle)
        if self._vehicle is None:
            LOGGER.error(
                "Vehicle %s not available for %s switch", vehicle, self._command_name
            )
            self._attr_available = False
            return
        self._attr_unique_id = f"{self._attr_unique_id}_{self._interval_key}"

    @property
    def _reported_state(self) -> bool:
        """Return the state reported by the vehicle."""
        raise NotImplementedError

    async def _send_command(self, active: bool) -> bool:
        """Send the command to the vehicle and return whether it was accepted."""
        raise NotImplementedError

    @property
    def is_on(self) -> bool:
        """Return the requested state while pending, else the reported state."""
        if self._pending_state is not None:
            return self._pending_state
        return self._reported_state

    def _clear_pending_state(self) -> None:
        self._pending_state = None
        self._pending_until = None
        self.coordinator.reset_update_interval(self._interval_key)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Drop the requested state once the vehicle confirms it or it times out."""
        if self._pending_state is not None and (
            self._reported_state == self._pending_state
            or dt_util.utcnow() >= self._pending_until
        ):
            self._clear_pending_state()
        super()._handle_coordinator_update()

    async def _set_state(self, active: bool) -> None:
        if self._vehicle is None:
            LOGGER.warning(
                "Cannot set %s; vehicle %s unavailable",
                self._command_name,
                self._vehicle_vin,
            )
            return
        LOGGER.debug(
            "Setting %s to %s for vehicle %s",
            self._command_name,
            active,
            self._vehicle.vin,
        )
        try:
            success = await self._send_command(active)
        except Exception:
            LOGGER.exception(
                "Error setting %s for vehicle %s",
                self._command_name,
                getattr(self._vehicle, "vin", "unknown"),
            )
            success = False

        if success:
            # Show the requested state until the vehicle reports it
            self._pending_state = active
            self._pending_until = dt_util.utcnow() + timedelta(
                seconds=PENDING_STATE_TIMEOUT
            )
            self.coordinator.set_update_interval(
                self._interval_key, timedelta(seconds=FAST_INTERVAL)
            )
        else:
            LOGGER.warning(
                "Vehicle %s did not accept the %s command",
                self._vehicle.vin,
                self._command_name,
            )
            self._clear_pending_state()
        self.async_write_ha_state()

        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the function on."""
        await self._set_state(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the function off."""
        await self._set_state(False)


class SmartDefrostSwitch(SmartPendingStateSwitch):
    """
    Switch entity for the front windscreen defrost of a Smart vehicle.

    The state follows the vehicle's reported `defrosting_active` climate value.
    Turning the switch on or off starts or stops the defrost via the RCE_2
    remote climate service.
    """

    _attr_icon = "mdi:car-defrost-front"
    _interval_key = "defrost_switch"
    _command_name = "front defrost"

    @property
    def translation_key(self):
        return "defrost_control"

    @property
    def _reported_state(self) -> bool:
        """Return the defrost state reported by the vehicle."""
        if self._vehicle is None or self._vehicle.climate is None:
            return False
        return bool(self._vehicle.climate.defrosting_active)

    async def _send_command(self, active: bool) -> bool:
        return await self._vehicle.climate_control.set_defrost(active)


@dataclass(frozen=True)
class HeatingSwitchDescription:
    """Describes a seat / steering wheel heating switch."""

    key: str
    icon: str
    locations: tuple[HeatingLocation, ...]
    # Climate status attributes; the switch is on when any of them is true
    status_attributes: tuple[str, ...]


HEATING_SWITCH_DESCRIPTIONS = (
    HeatingSwitchDescription(
        key="seat_heating",
        icon="mdi:car-seat-heater",
        locations=(HeatingLocation.DRIVER_SEAT, HeatingLocation.PASSENGER_SEAT),
        status_attributes=("driver_heating_status", "passenger_heating_status"),
    ),
    HeatingSwitchDescription(
        key="steering_wheel_heating",
        icon="mdi:steering",
        locations=(HeatingLocation.STEERING_WHEEL,),
        status_attributes=("steering_wheel_heating_status",),
    ),
)


class SmartHeatingSwitch(SmartPendingStateSwitch):
    """
    Switch entity that starts seat or steering wheel heating on its own.

    Unlike climate preconditioning, the air conditioning is not started. The
    levels come from the heating selects; locations set to "Off" are skipped,
    and if all are "Off" the default seat heating level is used for all of them.
    """

    def __init__(
        self,
        coordinator: SmartHashtagDataUpdateCoordinator,
        vehicle: str,
        description: HeatingSwitchDescription,
    ) -> None:
        """Initialize the heating switch."""
        self._description = description
        self._interval_key = f"{description.key}_switch"
        self._command_name = description.key.replace("_", " ")
        self._attr_icon = description.icon
        super().__init__(coordinator, vehicle)

    @property
    def translation_key(self):
        return f"{self._description.key}_control"

    @property
    def _reported_state(self) -> bool:
        """Return true if the vehicle reports heating on any of the locations."""
        if self._vehicle is None or self._vehicle.climate is None:
            return False
        return any(
            bool(getattr(self._vehicle.climate, attr, False))
            for attr in self._description.status_attributes
        )

    def _selected_levels(self) -> dict[HeatingLocation, int]:
        """Return the levels from the heating selects for this switch."""
        selects = self.coordinator.config_entry.data.get("selects", {})
        levels = {
            location: selects.get(location.value, 0)
            for location in self._description.locations
        }
        levels = {location: level for location, level in levels.items() if level > 0}
        if not levels:
            levels = dict.fromkeys(
                self._description.locations, DEFAULT_SEATHEATING_LEVEL
            )
        return levels

    async def _send_command(self, active: bool) -> bool:
        if active:
            levels = self._selected_levels()
        else:
            levels = dict.fromkeys(self._description.locations, 0)
        return await self._vehicle.climate_control.set_heating(active, levels)
