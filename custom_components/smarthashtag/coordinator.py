"""DataUpdateCoordinator for Smart #1/#3."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.const import CONF_SCAN_INTERVAL
from pysmarthashtag.account import SmartAccount
from pysmarthashtag.models import SmartAuthError, SmartAPIError
from pysmarthashtag.models import SmartRemoteServiceError

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .const import LOGGER


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
        self._update_intervals = {}

    async def _async_update_data(self):
        """Update data via library."""
        try:
            return await self.account.get_vehicles()
        except SmartAuthError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except SmartRemoteServiceError as exception:
            raise UpdateFailed(exception) from exception
        except SmartAPIError as exception:
            LOGGER.info(f"API access failed with: {exception}")

    def set_update_interval(self, key: str, deltatime: timedelta) -> None:
        """Update intervals by key and select the shortest"""
        LOGGER.info(f"Updatefrequency set for {key}: {deltatime}")
        self._update_intervals[key] = deltatime
        sorted_intervals = list(self._update_intervals.values())
        sorted_intervals.sort()
        if sorted_intervals:
            self.update_interval = sorted_intervals[0]

    def reset_update_interval(self, key: str):
        """Reset interval for this key to default"""
        self.set_update_interval(
            key,
            timedelta(
                seconds=self.config_entry.options.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                )
            ),
        )
