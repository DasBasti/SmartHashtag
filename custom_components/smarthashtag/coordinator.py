"""DataUpdateCoordinator for Smart #1/#3."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.exceptions import ConfigEntryAuthFailed

from pysmarthashtag.account import SmartAccount
from pysmarthashtag.models import (
    SmartAuthError,
    SmartRemoteServiceError,
)

from .const import DOMAIN, LOGGER

# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class SmartHashtagDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Smart Web API."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        account: SmartAccount,
    ) -> None:
        """Initialize."""
        self.account = account
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=5),
        )

    async def _async_update_data(self):
        """Update data via library."""
        try:
            return await self.account.get_vehicles()
        except SmartAuthError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except SmartRemoteServiceError as exception:
            raise UpdateFailed(exception) from exception
