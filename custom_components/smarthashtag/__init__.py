"""Smart #1/#3 for intergration with Home Assistant.

For more details about this integration, please refer to
https://github.com/DasBasti/SmartHashtag
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD
from homeassistant.const import CONF_USERNAME
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from pysmarthashtag.account import SmartAccount

from .coordinator import SmartHashtagDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.DEVICE_TRACKER,
    #    Platform.BINARY_SENSOR,
    #    Platform.SWITCH,
    Platform.CLIMATE,
    Platform.SELECT,
]

type SmartHashtagConfigEntry = ConfigEntry[SmartHashtagDataUpdateCoordinator]

# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry


async def async_setup_entry(
    hass: HomeAssistant, entry: SmartHashtagConfigEntry
) -> bool:
    """Set up this integration using UI."""
    entry.runtime_data = SmartHashtagDataUpdateCoordinator(
        hass=hass,
        account=SmartAccount(
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
        ),
        entry=entry,
    )
    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await entry.runtime_data.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
