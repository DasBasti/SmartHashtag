"""Fixtures for testing."""

import pytest
import respx
from pysmarthashtag.tests.conftest import (  # noqa: F401
    SmartMockRouter,
    smart_fixture,
)


@pytest.fixture(autouse=True)
def _auto_enable_custom_integrations(enable_custom_integrations):
    return


@pytest.fixture
def smart_intl_fixture(request: pytest.FixtureRequest, smart_fixture: respx.Router):
    """Extend smart_fixture with international endpoints."""
    # International API endpoints
    intl_api_base_url = "https://api.ecloudap.com"
    intl_api_base_url_v2 = "https://apiv2.ecloudap.com"

    # Add routes for international endpoints using correct response format
    for base_url in [intl_api_base_url, intl_api_base_url_v2]:
        smart_fixture.post(base_url + "/auth/account/session/secure?identity_type=smart").respond(
            200,
            json={
                "code": 1000,
                "data": {
                    "expiresIn": 4579200,
                    "deviceType": "mobile",
                    "clientId": "APPLE0000APP00IPHONE241P10804023",
                    "idToken": "",
                    "resultCode": "0",
                    "alias": "",
                    "accessToken": "eyJhbGciOiJIUzI1NiJ9.test_token",
                    "tcToken": "",
                    "resultMessage": "Success",
                    "userId": "112233",
                    "refreshToken": "ODMxREJENDIzMEJDNjc5NkEyNENCRDYxRjY3MjAwQzQ="
                },
                "success": True,
                "hint": None,
                "sessionId": None,
                "message": "Successful."
            },
        )
        # Mock both endpoints that might be used
        smart_fixture.get(base_url + "/basic/vehicle/list?needSharedCar=1&userId=112233").respond(
            200,
            json={
                "code": "1000",
                "message": None,
                "hint": None,
                "httpStatus": "OK",
                "data": {
                    "list": [
                        {
                            "vin": "TestVIN0000000001",
                            "modelName": "HX11_EUL_Premium+_RWD_000",
                            "defaultVehicle": True,
                            "seriesCodeVs": "HX11",
                            "seriesName": "HX11",
                            "colorName": "SPECTRUM BLUE",
                            "current": False,
                        }
                    ]
                },
                "sessionId": "test_session",
                "success": True
            },
        )
        smart_fixture.get(base_url + "/device-platform/user/vehicle/secure?needSharedCar=1&userId=112233").respond(
            200,
            json={
                "code": "1000",
                "message": None,
                "hint": None,
                "httpStatus": "OK",
                "data": {
                    "list": [
                        {
                            "vin": "TestVIN0000000001",
                            "modelName": "HX11_EUL_Premium+_RWD_000",
                            "defaultVehicle": True,
                            "seriesCodeVs": "HX11",
                            "seriesName": "HX11",
                            "colorName": "SPECTRUM BLUE",
                            "current": False,
                        }
                    ]
                },
                "sessionId": "test_session",
                "success": True
            },
        )
        smart_fixture.post(base_url + "/basic/vehicle/select").respond(200, json={"success": True})
        smart_fixture.get(
            base_url
            + "/remote-control/vehicle/status/TestVIN0000000001?latest=True&target=basic%2Cmore&userId=112233"
        ).respond(
            200,
            json={"data": {"status": "ok"}},
        )
        smart_fixture.put(base_url + "/remote-control/vehicle/telematics/TestVIN0000000001").respond(
            200, json={"data": {"success": True}}
        )
        smart_fixture.get(
            base_url + "/remote-control/vehicle/status/soc/TestVIN0000000001?setting=charging"
        ).respond(
            200,
            json={"data": {"soc": 90}},
        )

    return smart_fixture
