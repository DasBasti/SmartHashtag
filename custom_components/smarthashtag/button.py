"""Support for Smart buttons."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pysmarthashtag.control.horn_light import HornLightControl

from .const import CONF_VEHICLE, LOGGER
from .coordinator import SmartHashtagDataUpdateCoordinator
from .entity import SmartHashtagEntity

if TYPE_CHECKING:
    from . import SmartHashtagConfigEntry


@dataclass(frozen=True, kw_only=True)
class SmartButtonEntityDescription(ButtonEntityDescription):
    """Describes a Smart button and the command it sends."""

    press_fn: Callable[[HornLightControl], Awaitable[bool]]


BUTTON_DESCRIPTIONS = (
    SmartButtonEntityDescription(
        key="flash_lights",
        translation_key="flash_lights",
        icon="mdi:car-light-high",
        press_fn=lambda control: control.flash_lights(),
    ),
    SmartButtonEntityDescription(
        key="honk_horn",
        translation_key="honk_horn",
        icon="mdi:bullhorn",
        press_fn=lambda control: control.honk_horn(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: SmartHashtagConfigEntry, async_add_entities
):
    """Set up Smart button entities from a config entry."""
    coordinator = entry.runtime_data
    vehicle = coordinator.config_entry.data.get(CONF_VEHICLE)

    vehicles = coordinator.account.vehicles or {}
    if vehicle not in vehicles:
        LOGGER.error("Vehicle %s not available; skipping button setup", vehicle)
        return

    # Requires a pysmarthashtag release that provides Vehicle.horn_light_control
    if getattr(vehicles[vehicle], "horn_light_control", None) is None:
        LOGGER.warning(
            "Installed pysmarthashtag does not support horn and light control; "
            "skipping buttons"
        )
        return

    async_add_entities(
        SmartButton(coordinator, vehicle, description)
        for description in BUTTON_DESCRIPTIONS
    )


class SmartButton(SmartHashtagEntity, ButtonEntity):
    """
    Button entity for the find-my-car functions of a Smart vehicle.

    Pressing it sends the remote horn and light (RHL) command. The commands
    have no lasting state, so there is nothing to wait for or poll.
    """

    entity_description: SmartButtonEntityDescription

    def __init__(
        self,
        coordinator: SmartHashtagDataUpdateCoordinator,
        vehicle: str,
        description: SmartButtonEntityDescription,
    ) -> None:
        """Initialize the button class."""
        super().__init__(coordinator)
        self.entity_description = description
        self._vehicle_vin = vehicle
        self._vehicle = self.coordinator.account.vehicles.get(vehicle)
        if self._vehicle is None:
            LOGGER.error("Vehicle %s not available for %s", vehicle, description.key)
            self._attr_available = False
            return
        self._attr_unique_id = f"{self._attr_unique_id}_{description.key}"

    async def async_press(self) -> None:
        """Send the command to the vehicle."""
        if self._vehicle is None:
            raise HomeAssistantError(f"Vehicle {self._vehicle_vin} is unavailable")
        key = self.entity_description.key
        LOGGER.debug("Sending %s command to vehicle %s", key, self._vehicle.vin)
        try:
            success = await self.entity_description.press_fn(
                self._vehicle.horn_light_control
            )
        except Exception as err:
            raise HomeAssistantError(
                f"Failed to send {key} to vehicle {self._vehicle.vin}: {err}"
            ) from err
        if not success:
            raise HomeAssistantError(
                f"Vehicle {self._vehicle.vin} did not accept the {key} command"
            )
