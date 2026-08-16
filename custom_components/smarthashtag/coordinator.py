"""DataUpdateCoordinator for Smart #1/#3."""

from __future__ import annotations

import asyncio
import traceback
from datetime import timedelta
from typing import Any

import httpx
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pysmarthashtag.account import SmartAccount
from pysmarthashtag.models import SmartAPIError, SmartAuthError, SmartRemoteServiceError

try:
    # Typed "VIN no longer bound to this account" (cloud code 8040), added in the
    # token-lifecycle pysmarthashtag. Fall back to a never-raised placeholder on
    # older library versions so the except clause stays harmless.
    from pysmarthashtag.models import SmartVehicleUnboundError
except ImportError:  # pragma: no cover - depends on installed pysmarthashtag

    class SmartVehicleUnboundError(SmartAPIError):  # noqa: N818
        """Placeholder for older pysmarthashtag without the typed unbound error."""


from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER, UNBOUND_VIN_AUTH_MESSAGE

# Maximum consecutive transient failures before raising UpdateFailed
# Set high enough to tolerate multiple internal API calls failing within a single refresh
MAX_TRANSIENT_FAILURES = 10

# Consecutive 8040s before the VIN is considered genuinely unbound.
# A single 8040 is routinely transient: the cloud answers "no vehicle
# information bounded with this VIN and UID" for a moment right after a
# session refresh, before it re-associates the VIN with the new session,
# and the next poll succeeds. Escalating on the first one turns a blip
# into a reauth prompt that keeps every entity unavailable until someone
# reloads the entry by hand.
UNBOUND_FAILURES_BEFORE_REAUTH = 3

# Timeout (seconds) for a full vehicle data refresh. A healthy refresh is a
# chain of sequential Smart/Geely cloud calls that can legitimately take ~20s.
API_TIMEOUT = 30


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
        self._unbound_failures = 0
        self._last_error: str | None = None

    async def _async_setup(self) -> None:
        """
        Asynchronously set up the data update coordinator.

        This method is called when the coordinator is initialized. It sets the update interval
        based on the configuration entry options and prepares the coordinator for data updates.
        """
        try:
            await self.account.get_vehicles()
        except SmartVehicleUnboundError as exception:
            # Setup has no history to tell a transient 8040 from a real one, so
            # let HA retry with backoff instead of demanding reauth up front.
            # A genuine unbinding still surfaces from the update path.
            raise ConfigEntryNotReady(UNBOUND_VIN_AUTH_MESSAGE) from exception
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
            async with asyncio.timeout(API_TIMEOUT):
                await self.account.get_vehicles()
                # Reset failure counter on success
                if self._consecutive_failures > 0:
                    LOGGER.info(
                        "Smart API connection restored after %d failed attempts",
                        self._consecutive_failures,
                    )
                self._consecutive_failures = 0
                self._unbound_failures = 0
                self._last_error = None
                return self.account.vehicles
        except SmartVehicleUnboundError as exception:
            # Only terminal once it repeats: a lone 8040 is usually the cloud
            # catching up after a session refresh. Below the threshold it goes
            # through the normal transient path so cached data keeps the
            # entities alive and the next poll can clear it.
            self._unbound_failures += 1
            if self._unbound_failures < UNBOUND_FAILURES_BEFORE_REAUTH:
                LOGGER.warning(
                    "Vehicle reported as unbound (8040) %d/%d, treating as transient: %s",
                    self._unbound_failures,
                    UNBOUND_FAILURES_BEFORE_REAUTH,
                    exception,
                )
                return self._handle_transient_failure(exception)
            LOGGER.error("%s (8040): %s", UNBOUND_VIN_AUTH_MESSAGE, exception)
            raise ConfigEntryAuthFailed(UNBOUND_VIN_AUTH_MESSAGE) from exception
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
            return self._handle_transient_failure(exception)
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

    def _handle_transient_failure(self, exception: Exception) -> Any:
        """Serve cached data for a transient failure, or fail once it persists.

        Keeps entities alive across a cloud blip and only raises UpdateFailed
        when there is nothing cached or the failures stop looking transient.
        """
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
            and self._consecutive_failures < MAX_TRANSIENT_FAILURES
        ):
            LOGGER.debug("Returning cached data to keep entities available")
            return self.data

        # If no cached data or too many failures, raise UpdateFailed
        if self.data is None:
            LOGGER.info(
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
