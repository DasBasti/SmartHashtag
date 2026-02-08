"""Smart #1/#3 for intergration with Home Assistant.

For more details about this integration, please refer to
https://github.com/DasBasti/SmartHashtag
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from pysmarthashtag.account import SmartAccount
from pysmarthashtag.const import EndpointUrls

from .const import (
    CONF_API_BASE_URL,
    CONF_API_BASE_URL_V2,
    CONF_REGION,
    REGION_CUSTOM,
)
from .coordinator import SmartHashtagDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.DEVICE_TRACKER,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.CLIMATE,
    Platform.SELECT,
]

type SmartHashtagConfigEntry = ConfigEntry[SmartHashtagDataUpdateCoordinator]

# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry


async def async_setup_entry(
    hass: HomeAssistant, entry: SmartHashtagConfigEntry
) -> bool:
    """
    Initialize the Smart Hashtag integration from a UI configuration entry.

    This asynchronous function sets up the integration by creating and initializing a
    SmartHashtagDataUpdateCoordinator. It uses the Home Assistant instance along with
    credentials (username and password) provided in the configuration entry's data to
    instantiate a SmartAccount. The coordinator then performs an initial data refresh.
    Afterward, the function forwards the configuration entry to all supported platforms,
    and registers an update listener to handle future reloads of the configuration.

    Parameters:
        hass (HomeAssistant): The Home Assistant instance.
        entry (SmartHashtagConfigEntry): The configuration entry containing integration-specific
            data. Must include CONF_USERNAME and CONF_PASSWORD in its data dictionary.

    Returns:
        bool: True if setup was successful; otherwise, an exception may be raised during the process.
    """
    # Determine endpoint URLs based on region or custom settings
    endpoint_urls = None
    region = entry.data.get(CONF_REGION)

    if region == REGION_CUSTOM:
        # Use custom endpoints if provided
        custom_api_base_url = entry.data.get(CONF_API_BASE_URL)
        custom_api_base_url_v2 = entry.data.get(CONF_API_BASE_URL_V2)
        if custom_api_base_url or custom_api_base_url_v2:
            endpoint_urls = EndpointUrls(
                api_base_url=custom_api_base_url or None,
                api_base_url_v2=custom_api_base_url_v2 or None,
            )
    # For EU region (default) or unrecognized region, endpoint_urls remains None
    # and SmartAccount will use default EU endpoints

    entry.runtime_data = SmartHashtagDataUpdateCoordinator(
        hass=hass,
        account=SmartAccount(
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            endpoint_urls=endpoint_urls,
        ),
        entry=entry,
    )
    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await entry.runtime_data.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Asynchronously unload the platforms associated with a Home Assistant configuration entry.

    This function initiates the unloading process for all platforms specified in the
    PLATFORMS list for the given configuration entry. It delegates the operation to Home
    Assistant's asynchronous platform unload mechanism.

    Parameters:
        hass (HomeAssistant): The Home Assistant instance.
        entry (ConfigEntry): The configuration entry to be unloaded.

    Returns:
        bool: True if all platforms were successfully unloaded, False otherwise.

    Raises:
        Exception: Propagates any exceptions raised during the unload process.
    """
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """
    Reload the specified configuration entry.

    This function triggers a reload of the configuration entry by calling Home Assistant's
    config_entries.async_reload method using the entry's unique identifier. It is used to apply
    configuration changes on the fly without requiring a full restart of Home Assistant.

    Parameters:
        hass (HomeAssistant): The Home Assistant instance.
        entry (ConfigEntry): The configuration entry to be reloaded.

    Returns:
        None

    Raises:
        Exception: Propagates any exceptions raised by hass.config_entries.async_reload.
    """
    await hass.config_entries.async_reload(entry.entry_id)
