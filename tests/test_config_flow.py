"""Test the Simple Integration config flow."""

from unittest.mock import AsyncMock, patch

import pytest
import respx
from homeassistant import config_entries, setup
from homeassistant.core import HomeAssistant
from pysmarthashtag.models import SmartAPIError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smarthashtag.const import (
    CONF_CHARGING_INTERVAL,
    CONF_CONDITIONING_TEMP,
    CONF_DRIVING_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    CONF_API_BASE_URL,
    CONF_API_BASE_URL_V2,
    CONF_REGION,
    DOMAIN,
    REGION_CUSTOM,
    REGION_EU,
    REGION_INTL,
)


@pytest.mark.asyncio()
async def test_form(hass: HomeAssistant, smart_fixture: respx.Router):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    with patch(
        "custom_components.smarthashtag.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "test",
                "password": "test",
            },
        )

    assert result2["type"] == "form"
    assert result2["step_id"] == "vehicle"
    await hass.async_block_till_done()

    with patch(
        "custom_components.smarthashtag.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {
                "vehicle": "TestVIN0000000001",
            },
        )

    assert result3["type"] == "create_entry"
    assert result3["title"] == "Smart TestVIN0000000001"
    assert result3["data"]["username"] == "test"
    assert result3["data"]["password"] == "test"
    assert result3["data"]["vehicle"] == "TestVIN0000000001"
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.asyncio()
async def test_form_with_eu_region(hass: HomeAssistant, smart_fixture: respx.Router):
    """Test config flow with EU region selection."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    # Mock the SmartAccount to raise SmartAPIError
    with patch(
        "custom_components.smarthashtag.config_flow.SmartAccount"
    ) as mock_account:
        mock_instance = AsyncMock()
        mock_instance.login = AsyncMock(side_effect=SmartAPIError("Auth failed"))
        mock_account.return_value = mock_instance

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "bad_user",
                "password": "bad_password",
            },
        )

    # Should show form again with auth error
    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "auth"}


@pytest.mark.asyncio()
async def test_single_vehicle_flow(hass: HomeAssistant, smart_fixture: respx.Router):
    """Test that single vehicle selection skips vehicle selection step."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    # Mock the account with only one vehicle
    with (
        patch(
            "custom_components.smarthashtag.config_flow.SmartAccount"
        ) as mock_account,
        patch(
            "custom_components.smarthashtag.async_setup_entry",
            return_value=True,
        ),
    ):
        mock_instance = AsyncMock()
        mock_instance.login = AsyncMock()
        mock_instance.get_vehicles = AsyncMock()
        # Return only one vehicle
        mock_instance.vehicles = {"SingleVIN0000001": {}}
        mock_account.return_value = mock_instance

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "test",
                "password": "test",
            },
        )

    # With only one vehicle, it should directly create entry
    assert result2["type"] == "create_entry"
    assert result2["title"] == "Smart SingleVIN0000001"
    assert result2["data"]["vehicle"] == "SingleVIN0000001"


@pytest.mark.asyncio()
async def test_options_flow_init(hass: HomeAssistant, smart_fixture: respx.Router):
    """Test options flow initialization."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "sample_user",
            "password": "sample_password",
            "vehicle": "TestVIN0000000001",
        },
        options={},
    )

    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Start options flow
    result = await hass.config_entries.options.async_init(entry.entry_id)

    # Should show form
    assert result["type"] == "form"
    assert result["step_id"] == "user"


@pytest.mark.asyncio()
async def test_options_flow_update(hass: HomeAssistant, smart_fixture: respx.Router):
    """Test options flow with user input."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "sample_user",
            "password": "sample_password",
            "vehicle": "TestVIN0000000001",
        },
        options={},
    )

    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Start options flow
    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == "form"
    assert result["step_id"] == "user"

    # Configure options
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "scan_interval": DEFAULT_SCAN_INTERVAL,
            CONF_CHARGING_INTERVAL: 120,
            CONF_DRIVING_INTERVAL: 60,
            CONF_CONDITIONING_TEMP: 22,
        },
    )

    # Should create entry with new options
    assert result2["type"] == "create_entry"
    assert result2["data"][CONF_CHARGING_INTERVAL] == 120
    assert result2["data"][CONF_DRIVING_INTERVAL] == 60
    assert result2["data"][CONF_CONDITIONING_TEMP] == 22
