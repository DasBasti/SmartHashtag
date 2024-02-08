"""Adds config flow for Smart #1/#3 integration."""
from __future__ import annotations
from typing import Final, KeysView

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD
from homeassistant.const import CONF_USERNAME
from homeassistant.helpers import selector
from pysmarthashtag.account import SmartAccount
from pysmarthashtag.models import (
    SmartAPIError,
)

from .const import DOMAIN
from .const import LOGGER

CONF_VEHICLE: Final = "vehicle"
CONF_VEHICLES: Final = "vehicles"


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
                self.init_info[CONF_VEHICLES] = vehicles
                return await self.async_step_vehicle()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME,
                        default=(user_input or {}).get(CONF_USERNAME),
                        description={"suggested_value": "username"},
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.EMAIL,
                            autocomplete="username",
                        ),
                    ),
                    vol.Required(
                        CONF_PASSWORD, description={"suggested_value": "password"}
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
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_USERNAME],
                data={**self.init_info, **user_input},
            )

        return await self.async_show_form(
            step_id="vehicle",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_VEHICLE): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=self.init_info[CONF_VEHICLES],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
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
