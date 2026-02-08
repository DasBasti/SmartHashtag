"""DataUpdateCoordinator for Smart #1/#3."""

from __future__ import annotations

import asyncio
import traceback
from datetime import timedelta

import async_timeout
import httpx
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pysmarthashtag.account import SmartAccount
from pysmarthashtag.models import SmartAPIError, SmartAuthError, SmartRemoteServiceError

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER

# Maximum consecutive transient failures before raising UpdateFailed
# Set high enough to tolerate multiple internal API calls failing within a single refresh
MAX_TRANSIENT_FAILURES = 10


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
        self._consecutive_failures = 0
        self._last_error: str | None = None

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
        return the last known data to keep entities available.

        Returns:
            Any: The vehicle data as returned by self.account.get_vehicles(), or the
                 last known data if a SmartAPIError or HTTP error is encountered.

        Note:
            self.data can be None in the following scenarios:
            - On first run if the API call fails (SmartAPIError or HTTP error)
            - During entity setup before the first successful data fetch
            - If coordinator initialization fails
            All entity properties that access self.data or self.account.vehicles
            must handle None values gracefully to prevent AttributeError during
            entity registration.

        Raises:
            ConfigEntryAuthFailed: If a SmartAuthError is caught, indicating an authentication failure.
            UpdateFailed: If a SmartRemoteServiceError is raised during the data retrieval.
        """
        try:
            async with async_timeout.timeout(10):
                await self.account.get_vehicles()
                # Reset failure counter on success
                if self._consecutive_failures > 0:
                    LOGGER.info(
                        "Smart API connection restored after %d failed attempts",
                        self._consecutive_failures,
                    )
                self._consecutive_failures = 0
                self._last_error = None
                return self.account.vehicles
        except SmartAuthError as exception:
            LOGGER.error(
                "Authentication failed for Smart API: %s. "
                "Please check your credentials.",
                exception,
            )
            raise ConfigEntryAuthFailed(exception) from exception
        except SmartRemoteServiceError as exception:
            LOGGER.error(
                "Smart remote service error: %s",
                exception,
            )
            raise UpdateFailed(f"Remote service error: {exception}") from exception
        except (
            SmartAPIError,
            httpx.HTTPStatusError,
            asyncio.TimeoutError,
            TimeoutError,
            httpx.ConnectError,
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            OSError,
            ConnectionError,
        ) as exception:
            self._consecutive_failures += 1
            error_type = type(exception).__name__
            error_msg = f"{error_type}: {exception}" if str(exception) else error_type

            # Only log if error changed or first occurrence
            if self._last_error != error_msg:
                LOGGER.warning(
                    "Smart API request failed (attempt %d/%d): %s",
                    self._consecutive_failures,
                    MAX_TRANSIENT_FAILURES,
                    error_msg,
                )
                self._last_error = error_msg

            # Return last known data to keep entities available if we have it
            # and haven't exceeded max failures
            if (
                self.data is not None
                and self._consecutive_failures <= MAX_TRANSIENT_FAILURES
            ):
                LOGGER.debug("Returning cached data to keep entities available")
                return self.data

            # If no cached data or too many failures, raise UpdateFailed
            if self.data is None:
                LOGGER.error(
                    "Smart API unavailable and no cached data exists: %s",
                    error_msg,
                )
                raise UpdateFailed(
                    f"API unavailable with no cached data: {error_msg}"
                ) from exception

            LOGGER.error(
                "Smart API unavailable after %d consecutive failures: %s",
                self._consecutive_failures,
                error_msg,
            )
            raise UpdateFailed(
                f"API unavailable after {self._consecutive_failures} attempts: {error_msg}"
            ) from exception
        except Exception as exception:
            error_type = type(exception).__name__
            error_msg = str(exception) or "No error message"
            LOGGER.error(
                "Unexpected error fetching Smart API data: %s: %s\n%s",
                error_type,
                error_msg,
                traceback.format_exc(),
            )
            raise UpdateFailed(
                f"Unexpected error ({error_type}): {error_msg}"
            ) from exception

    def set_update_interval(self, key: str, deltatime: timedelta) -> None:
        """Update intervals by key and select the shortest"""
        LOGGER.info(f"Updatefrequency set for {key}: {deltatime}")
        self._update_intervals[key] = deltatime
        sorted_intervals = list(self._update_intervals.values())
        sorted_intervals.sort()
        if sorted_intervals:
            self.update_interval = sorted_intervals[0]

    def reset_update_interval(self, key: str):
        """Remove interval for this key and select shortest remaining or default"""
        if key in self._update_intervals:
            del self._update_intervals[key]
            LOGGER.info("Update frequency reset for %s", key)

        # Recalculate the update interval
        if self._update_intervals:
            sorted_intervals = list(self._update_intervals.values())
            sorted_intervals.sort()
            self.update_interval = sorted_intervals[0]
        elif self.config_entry:
            # No active intervals, revert to configured default
            self.update_interval = timedelta(
                seconds=self.config_entry.options.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                )
            )
        else:
            # Fallback to default if no config entry
            self.update_interval = timedelta(seconds=DEFAULT_SCAN_INTERVAL)
            LOGGER.warning("Using fallback update interval due to missing config_entry")
