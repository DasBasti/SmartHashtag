"""Adds config flow for Smart #1/#3 integration."""
from __future__ import annotations
from typing import KeysView

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers import config_validation as cv
from pysmarthashtag.account import SmartAccount
from pysmarthashtag.models import (
    SmartAPIError,
)

from .const import (
    CONF_CHARGING_INTERVAL,
    CONF_CONDITIONING_TEMP,
    CONF_DRIVING_INTERVAL,
    DEFAULT_CHARGING_INTERVAL,
    DEFAULT_CONDITIONING_TEMP,
    DEFAULT_DRIVING_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
    NAME,
)
from .const import LOGGER
from .const import CONF_VEHICLE
from .const import CONF_VEHICLES


class SmartHashtagFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Smart #1 / #3 integration."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            try:
                vehicles = await self._test_credentials(
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
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

    async def _test_credentials(self, username: str, password: str) -> KeysView[str]:
        """Validate credentials."""
        client = SmartAccount(
            username=username,
            password=password,
        )
        await client.login()
        await client.get_vehicles()
        return client.vehicles.keys()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):  # pylint: disable=unused-argument
        """Get the options flow for this handler."""
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle a option flow for Smart."""

    @property
    def config_entry(self):
        return self.hass.config_entries.async_get_entry(self.handler)

    async def async_step_init(self, user_input=None):  # pylint: disable=unused-argument
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle options flow initialized by the user."""
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
