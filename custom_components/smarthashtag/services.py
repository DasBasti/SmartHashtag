"""Services of the Smart integration."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_DEVICE_ID, ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_VEHICLE, DOMAIN, LOGGER
from .share import SharedLocationError, async_resolve_shared_location

SERVICE_SEND_DESTINATION = "send_destination"
SERVICE_SEND_SHARED_DESTINATION = "send_shared_destination"

ATTR_NAME = "name"
ATTR_ADDRESS = "address"
ATTR_URL = "url"

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


SEND_SHARED_DESTINATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_URL): cv.string,
    }
)


def _get_vehicle(hass: HomeAssistant, device_id: str):
    """Return the account and VIN of the vehicle behind a device."""
    device = dr.async_get(hass).async_get(device_id)
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
    return account, vin


async def _send_destination(
    account, vin: str, latitude: float, longitude: float, name: str, address: str
) -> None:
    """Send a destination to the vehicle and raise if it is not accepted."""
    LOGGER.debug("Sending destination to vehicle %s", vin)
    try:
        success = await account.send_destination_to_car(
            vin, latitude, longitude, name, address
        )
    except (TypeError, ValueError) as err:
        raise ServiceValidationError(str(err)) from err
    except Exception as err:
        raise HomeAssistantError(
            f"Failed to send the destination to vehicle {vin}: {err}"
        ) from err
    if not success:
        raise HomeAssistantError(f"Vehicle {vin} did not accept the destination")


def async_setup_services(hass: HomeAssistant) -> None:
    """Register the services of the integration."""

    async def _async_send_destination(call: ServiceCall) -> None:
        """Send a destination to the navigation system of the vehicle."""
        account, vin = _get_vehicle(hass, call.data[ATTR_DEVICE_ID])
        await _send_destination(
            account,
            vin,
            call.data[ATTR_LATITUDE],
            call.data[ATTR_LONGITUDE],
            call.data[ATTR_NAME],
            call.data[ATTR_ADDRESS],
        )

    async def _async_send_shared_destination(call: ServiceCall) -> None:
        """Resolve a location shared from a maps app and send it to the vehicle."""
        account, vin = _get_vehicle(hass, call.data[ATTR_DEVICE_ID])
        try:
            location = await async_resolve_shared_location(
                async_get_clientsession(hass), call.data[ATTR_URL]
            )
        except SharedLocationError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="shared_location_unresolved",
                translation_placeholders={"reason": str(err)},
            ) from err
        await _send_destination(
            account,
            vin,
            location.latitude,
            location.longitude,
            location.name,
            location.address,
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_DESTINATION,
        _async_send_destination,
        schema=SEND_DESTINATION_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_SHARED_DESTINATION,
        _async_send_shared_destination,
        schema=SEND_SHARED_DESTINATION_SCHEMA,
    )
