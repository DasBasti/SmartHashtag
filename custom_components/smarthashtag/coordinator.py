"""DataUpdateCoordinator for Smart #1/#3."""

from __future__ import annotations

from datetime import timedelta

import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pysmarthashtag.account import SmartAccount
from pysmarthashtag.models import SmartAPIError, SmartAuthError, SmartRemoteServiceError

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class SmartHashtagDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Smart Web API."""

    config_entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, account: SmartAccount, *, entry: ConfigEntry
    ) -> None:
        """
        Initialize a SmartHashtagDataUpdateCoordinator instance.

        This constructor sets up the data update coordinator with the provided Home Assistant
        instance, Smart account, and configuration entry. It initializes the coordinator with a
        default update interval of 5 minutes and prepares an internal dictionary to track update
        intervals for various keys.

        Parameters:
            hass (HomeAssistant): The Home Assistant instance.
            account (SmartAccount): An instance used to interact with the Smart Web API.
            entry (ConfigEntry): The configuration entry containing integration settings.
        """
        self.account = account
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=5),
            config_entry=entry,
        )
        self._update_intervals = {}

    async def _async_setup(self) -> None:
        """
        Asynchronously set up the data update coordinator.

        This method is called when the coordinator is initialized. It sets the update interval
        based on the configuration entry options and prepares the coordinator for data updates.
        """
        try:
            await self.account.get_vehicles()
        except SmartAuthError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except SmartRemoteServiceError as exception:
            raise UpdateFailed(exception) from exception
        except SmartAPIError as exception:
            LOGGER.info(f"API access failed with: {exception}")
        except Exception as exception:
            raise UpdateFailed(exception) from exception

    async def _async_update_data(self):
        """
        Asynchronously fetch vehicle data from the Smart API.

        This coroutine retrieves the latest vehicle data by calling the account's
        asynchronous get_vehicles method. Authentication and remote service issues are
        handled by raising appropriate exceptions, while any API errors are logged and
        result in a None return value.

        Returns:
            Any: The vehicle data as returned by self.account.get_vehicles(), or None if a
                 SmartAPIError is encountered.

        Raises:
            ConfigEntryAuthFailed: If a SmartAuthError is caught, indicating an authentication failure.
            UpdateFailed: If a SmartRemoteServiceError is raised during the data retrieval.
        """
        try:
            async with async_timeout.timeout(10):
                await self.account.get_vehicles()
                return self.account.vehicles
        except SmartAuthError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except SmartRemoteServiceError as exception:
            raise UpdateFailed(exception) from exception
        except SmartAPIError as exception:
            LOGGER.info(f"API access failed with: {exception}")
        except Exception as exception:
            raise UpdateFailed(exception) from exception

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
        if self.config_entry:
            self.set_update_interval(
                key,
                timedelta(
                    seconds=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    )
                ),
            )
        else:
            LOGGER.warning("Cannot reset update interval due to missing config_entry")
