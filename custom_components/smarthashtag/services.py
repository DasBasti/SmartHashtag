"""Services of the Smart integration."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_DEVICE_ID, ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .const import CONF_VEHICLE, DOMAIN, LOGGER

SERVICE_SEND_DESTINATION = "send_destination"

ATTR_NAME = "name"
ATTR_ADDRESS = "address"

SEND_DESTINATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_LATITUDE): vol.All(
            vol.Coerce(float), vol.Range(min=-90, max=90)
        ),
        vol.Required(ATTR_LONGITUDE): vol.All(
            vol.Coerce(float), vol.Range(min=-180, max=180)
        ),
        vol.Required(ATTR_NAME): vol.All(cv.string, vol.Length(min=1)),
        vol.Optional(ATTR_ADDRESS, default=""): cv.string,
    }
)


def async_setup_services(hass: HomeAssistant) -> None:
    """Register the services of the integration."""

    async def _async_send_destination(call: ServiceCall) -> None:
        """Send a destination to the navigation system of the vehicle."""
        device = dr.async_get(hass).async_get(call.data[ATTR_DEVICE_ID])
        entry = None
        if device is not None:
            for entry_id in device.config_entries:
                candidate = hass.config_entries.async_get_entry(entry_id)
                if candidate is not None and candidate.domain == DOMAIN:
                    entry = candidate
                    break
        if entry is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="device_not_found",
            )
        if entry.state is not ConfigEntryState.LOADED:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="entry_not_loaded",
            )

        account = entry.runtime_data.account
        vin = entry.data.get(CONF_VEHICLE)
        if vin not in (account.vehicles or {}):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="device_not_found",
            )

        LOGGER.debug("Sending destination to vehicle %s", vin)
        try:
            success = await account.send_destination_to_car(
                vin,
                call.data[ATTR_LATITUDE],
                call.data[ATTR_LONGITUDE],
                call.data[ATTR_NAME],
                call.data[ATTR_ADDRESS],
            )
        except (TypeError, ValueError) as err:
            raise ServiceValidationError(str(err)) from err
        except Exception as err:
            raise HomeAssistantError(
                f"Failed to send the destination to vehicle {vin}: {err}"
            ) from err
        if not success:
            raise HomeAssistantError(f"Vehicle {vin} did not accept the destination")

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_DESTINATION,
        _async_send_destination,
        schema=SEND_DESTINATION_SCHEMA,
    )
