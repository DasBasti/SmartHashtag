"""Test the Simple Integration config flow."""

from unittest.mock import patch

import pytest
import respx
from homeassistant import config_entries, setup
from homeassistant.core import HomeAssistant

from custom_components.smarthashtag.const import (
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

    with patch(
        "custom_components.smarthashtag.async_setup_entry",
        return_value=True,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "test",
                "password": "test",
                CONF_REGION: REGION_EU,
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
    assert result3["data"][CONF_REGION] == REGION_EU
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.asyncio()
async def test_form_with_intl_region(
    hass: HomeAssistant, smart_intl_fixture: respx.Router
):
    """Test config flow with International region selection."""
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
                CONF_REGION: REGION_INTL,
            },
        )

    # When there's only one vehicle, it auto-creates the entry
    assert result2["type"] == "create_entry"
    assert result2["data"][CONF_REGION] == REGION_INTL
    assert result2["data"]["username"] == "test"
    assert result2["data"]["password"] == "test"
    assert result2["data"]["vehicle"] == "TestVIN0000000001"
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.asyncio()
async def test_form_with_custom_endpoints(
    hass: HomeAssistant, smart_intl_fixture: respx.Router
):
    """Test config flow with custom endpoints."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    # Select custom region
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "username": "test",
            "password": "test",
            CONF_REGION: REGION_CUSTOM,
        },
    )

    assert result2["type"] == "form"
    assert result2["step_id"] == "custom_endpoints"

    # Configure custom endpoints
    with patch(
        "custom_components.smarthashtag.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {
                CONF_API_BASE_URL: "https://api.ecloudap.com",
                CONF_API_BASE_URL_V2: "https://apiv2.ecloudap.com",
            },
        )

    # When there's only one vehicle, it auto-creates the entry
    assert result3["type"] == "create_entry"
    assert result3["data"][CONF_REGION] == REGION_CUSTOM
    assert result3["data"][CONF_API_BASE_URL] == "https://api.ecloudap.com"
    assert result3["data"][CONF_API_BASE_URL_V2] == "https://apiv2.ecloudap.com"
    assert result3["data"]["vehicle"] == "TestVIN0000000001"
    assert len(mock_setup_entry.mock_calls) == 1
