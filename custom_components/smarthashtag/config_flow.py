"""Adds config flow for Smart #1/#3 integration."""

from __future__ import annotations

from typing import KeysView

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector
from pysmarthashtag import EndpointUrls, SmartRegion, get_endpoint_urls_for_region
from pysmarthashtag.account import SmartAccount
from pysmarthashtag.models import (
    SmartAPIError,
)

from .const import (
    CONF_API_BASE_URL,
    CONF_API_BASE_URL_V2,
    CONF_CHARGING_INTERVAL,
    CONF_CONDITIONING_TEMP,
    CONF_DRIVING_INTERVAL,
    CONF_REGION,
    CONF_VEHICLE,
    CONF_VEHICLES,
    DEFAULT_CHARGING_INTERVAL,
    DEFAULT_CONDITIONING_TEMP,
    DEFAULT_DRIVING_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_REGION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
    MIN_SCAN_INTERVAL,
    NAME,
    REGION_CUSTOM,
    REGION_EU,
    REGION_INTL,
    REGIONS,
)


class SmartHashtagFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Smart #1 / #3 integration."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.init_info: dict = {}

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            # Check if custom endpoints are selected and redirect to custom step
            if user_input.get(CONF_REGION) == REGION_CUSTOM:
                self.init_info = user_input
                return await self.async_step_custom_endpoints()

            try:
                vehicles = await self._test_credentials(
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                    region=user_input.get(CONF_REGION, DEFAULT_REGION),
                )
            except SmartAPIError as exception:
                LOGGER.warning(exception)
                _errors["base"] = "auth"
            else:
                self.init_info = user_input
                self.init_info[CONF_VEHICLES] = list(vehicles)
                return await self.async_step_vehicle()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME,
                        default=(user_input or {}).get(CONF_USERNAME),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.EMAIL,
                            autocomplete="username",
                        ),
                    ),
                    vol.Required(
                        CONF_PASSWORD,
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                            autocomplete="current-password",
                        ),
                    ),
                    vol.Optional(
                        CONF_REGION,
                        default=(user_input or {}).get(CONF_REGION, DEFAULT_REGION),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(value=k, label=v)
                                for k, v in REGIONS.items()
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        ),
                    ),
                }
            ),
            errors=_errors,
        )

    async def async_step_vehicle(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        if len(self.init_info[CONF_VEHICLES]) == 1 or user_input is not None:
            if user_input is None:
                user_input = {CONF_VEHICLE: self.init_info[CONF_VEHICLES][0]}
            name = f"{NAME} {user_input[CONF_VEHICLE]}"
            await self.async_set_unique_id(name)
            return self.async_create_entry(
                title=name,
                data={**self.init_info, **user_input},
            )

        return self.async_show_form(
            step_id="vehicle",
            data_schema=vol.Schema(
                {vol.Required(CONF_VEHICLE): vol.In(self.init_info[CONF_VEHICLES])}
            ),
        )

    async def async_step_custom_endpoints(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle custom endpoints configuration."""
        _errors = {}
        if user_input is not None:
            try:
                vehicles = await self._test_credentials(
                    username=self.init_info[CONF_USERNAME],
                    password=self.init_info[CONF_PASSWORD],
                    custom_api_base_url=user_input.get(CONF_API_BASE_URL),
                    custom_api_base_url_v2=user_input.get(CONF_API_BASE_URL_V2),
                )
            except SmartAPIError as exception:
                LOGGER.warning(exception)
                _errors["base"] = "auth"
            else:
                # Merge custom endpoint info with init_info
                self.init_info[CONF_API_BASE_URL] = user_input.get(CONF_API_BASE_URL)
                self.init_info[CONF_API_BASE_URL_V2] = user_input.get(
                    CONF_API_BASE_URL_V2
                )
                self.init_info[CONF_VEHICLES] = list(vehicles)
                return await self.async_step_vehicle()

        return self.async_show_form(
            step_id="custom_endpoints",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_API_BASE_URL,
                        default=(user_input or {}).get(CONF_API_BASE_URL, ""),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.URL,
                        ),
                    ),
                    vol.Optional(
                        CONF_API_BASE_URL_V2,
                        default=(user_input or {}).get(CONF_API_BASE_URL_V2, ""),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.URL,
                        ),
                    ),
                }
            ),
            errors=_errors,
        )

    async def _test_credentials(
        self,
        username: str,
        password: str,
        region: str | None = None,
        custom_api_base_url: str | None = None,
        custom_api_base_url_v2: str | None = None,
    ) -> KeysView[str]:
        """Validate credentials."""
        endpoint_urls = None

        # Determine which endpoint URLs to use
        if custom_api_base_url or custom_api_base_url_v2:
            # Custom endpoints
            endpoint_urls = EndpointUrls(
                api_base_url=custom_api_base_url or None,
                api_base_url_v2=custom_api_base_url_v2 or None,
            )
        elif region and region != REGION_CUSTOM:
            # Predefined region
            if region == REGION_EU:
                endpoint_urls = get_endpoint_urls_for_region(SmartRegion.EU)
            elif region == REGION_INTL:
                endpoint_urls = get_endpoint_urls_for_region(SmartRegion.INTL)

        client = SmartAccount(
            username=username,
            password=password,
            endpoint_urls=endpoint_urls,
        )
        await client.login()
        await client.get_vehicles()
        return client.vehicles.keys()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):  # pylint: disable=unused-argument
        """
        Return an instance of OptionsFlowHandler for managing options in the Smart integration.

        This function creates and returns a new OptionsFlowHandler object to manage the options flow. The provided configuration entry is not used in the instantiation but is maintained for compatibility with the Home Assistant interface.

        Parameters:
            config_entry (ConfigEntry): The configuration entry for the integration (unused).

        Returns:
            OptionsFlowHandler: A new instance responsible for handling the integration's options flow.
        """
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle a option flow for Smart."""

    @property
    def config_entry(self):
        """
        Retrieve the current configuration entry for the options flow.

        This property fetches the configuration entry from Home Assistant's configuration entries
        using the handler associated with this flow. It provides a convenient way to access the active
        configuration details for further processing within the options flow.

        Returns:
            ConfigEntry: The active configuration entry.
        """
        return self.hass.config_entries.async_get_entry(self.handler)

    async def async_step_init(self, user_input=None):  # pylint: disable=unused-argument
        """
        Initializes the options flow for the integration.

        This asynchronous method serves as the entry point for the options configuration flow.
        It delegates handling of user input to the async_step_user method, allowing for reuse of common
        logic for processing and validating option settings.

        Parameters:
            user_input (Any, optional): User-provided input data for the options update. This parameter is unused and provided only for compatibility.

        Returns:
            Coroutine: A coroutine that resolves with the result from the async_step_user call, representing the outcome of this step in the options flow.
        """
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """
        Handle the options configuration step during the integration's options flow.

        If user_input is provided, logs the updated options using a debug message and creates a new configuration entry with the title set to DEFAULT_NAME. If no input is provided, returns a form with a data schema for user selection. The schema enforces that the values for CONF_SCAN_INTERVAL, CONF_CHARGING_INTERVAL, CONF_DRIVING_INTERVAL, and CONF_CONDITIONING_TEMP are positive integers and not below a defined minimum (MIN_SCAN_INTERVAL). Default values are pulled from the current configuration entry options or fall back to predefined defaults.

        Parameters:
            user_input (Optional[dict]): Dictionary containing the user-supplied options. If None, the form for entering options is displayed.

        Returns:
            An awaitable result that either creates a new configuration entry with the provided options or presents a form for user input.
        """
        if user_input is not None:
            LOGGER.debug("Update Options for %s: %s", DEFAULT_NAME, user_input)
            return self.async_create_entry(title=DEFAULT_NAME, data=user_input)

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): vol.All(cv.positive_int, vol.Clamp(min=MIN_SCAN_INTERVAL)),
                vol.Optional(
                    CONF_CHARGING_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_CHARGING_INTERVAL, DEFAULT_CHARGING_INTERVAL
                    ),
                ): vol.All(cv.positive_int, vol.Clamp(min=MIN_SCAN_INTERVAL)),
                vol.Optional(
                    CONF_DRIVING_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_DRIVING_INTERVAL, DEFAULT_DRIVING_INTERVAL
                    ),
                ): vol.All(cv.positive_int, vol.Clamp(min=MIN_SCAN_INTERVAL)),
                vol.Optional(
                    CONF_CONDITIONING_TEMP,
                    default=self.config_entry.options.get(
                        CONF_CONDITIONING_TEMP, DEFAULT_CONDITIONING_TEMP
                    ),
                ): vol.All(cv.positive_int, vol.Clamp(min=MIN_SCAN_INTERVAL)),
            }
        )
        return self.async_show_form(step_id="user", data_schema=data_schema)
