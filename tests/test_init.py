import pytest
import respx
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smarthashtag.const import DOMAIN


@pytest.mark.skip("Not implemented")
async def test_component_reload(hass: HomeAssistant, smart_fixture: respx.Router):
    """
    Test the sensors function

    This loads a sample testing configuration from the pysmarthashtag package and checks that the sensors are updated correctly.
    """

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "sample_user",
            "password": "sample_password",
            "vehicle": "TestVIN0000000001",
        },
    )

    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await entry.runtime_data.async_refresh()

    assert await entry.runtime_data.async_reload(entry.entry_id)
