"""The frame password goes to the frame and nowhere else.

v2.12.0 fetched the firmware release notes from GitHub through the
coordinator's authenticated session, which attached the frame's Basic
``Authorization`` header to that request too. These tests pin the fix: the
header is attached under the frame's base URL only, and the GitHub request
goes through Home Assistant's plain session.
"""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.const import CONF_PASSWORD
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.esp32_photoframe.const import (
    API_BATTERY,
    API_CONFIG,
    API_CURRENT_IMAGE,
    API_OTA_STATUS,
    API_PROCESSING_SETTINGS,
    API_SENSOR,
    API_SYSTEM_INFO,
    CONF_HOST,
    DOMAIN,
)
from custom_components.esp32_photoframe.coordinator import (
    PhotoFrameCoordinator,
    frame_authorization,
)
from custom_components.esp32_photoframe.update import (
    _GITHUB_RELEASE_API,
    PhotoFrameFirmwareUpdate,
)

FRAME = "http://192.168.1.50"
PASSWORD = "s3cret"
AUTH = frame_authorization(PASSWORD)
GITHUB = _GITHUB_RELEASE_API.format(tag="v2.20.1")


@pytest.fixture
def entry(hass):
    """A configured frame with a password."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: FRAME, CONF_PASSWORD: PASSWORD},
        entry_id="frame1",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def update_entity(hass, entry):
    """The Firmware update entity on a frame that has an update waiting."""
    coordinator = PhotoFrameCoordinator(hass, entry)
    coordinator.data = {
        "ota": {
            "current_version": "v2.20.0",
            "latest_version": "v2.20.1",
            "state": "update_available",
        },
        "system_info": {},
    }
    entity = PhotoFrameFirmwareUpdate(coordinator, entry)
    entity.hass = hass
    entity.async_write_ha_state = MagicMock()
    return entity


def _headers_of(aioclient_mock: AiohttpClientMocker, url: str) -> dict:
    for method, called_url, data, headers in aioclient_mock.mock_calls:
        if str(called_url) == url:
            return dict(headers or {})
    raise AssertionError(f"no request to {url}")


async def test_release_notes_do_not_carry_the_frame_password(hass, aioclient_mock, update_entity):
    """The v2.12.0 regression: release notes went out with the frame's header."""
    aioclient_mock.get(GITHUB, json={"body": "notes"})

    assert await update_entity.async_release_notes() == "notes"

    headers = _headers_of(aioclient_mock, GITHUB)
    assert "Authorization" not in headers
    assert headers["Accept"] == "application/vnd.github+json"


async def test_ota_requests_carry_the_frame_password(hass, aioclient_mock, update_entity):
    """The frame's own OTA endpoints still authenticate."""
    aioclient_mock.post(
        f"{FRAME}/api/ota/check", json={"status": "success", "update_available": True}
    )
    aioclient_mock.post(f"{FRAME}/api/ota/update", json={"status": "success"})

    with patch.object(update_entity, "_async_track_install"):
        await update_entity.async_install(None, False)

    assert _headers_of(aioclient_mock, f"{FRAME}/api/ota/check")["Authorization"] == AUTH
    assert _headers_of(aioclient_mock, f"{FRAME}/api/ota/update")["Authorization"] == AUTH


async def test_every_poll_carries_the_frame_password(hass, aioclient_mock, entry):
    """A coordinator refresh authenticates each request, and only talks to the frame."""
    aioclient_mock.get(f"{FRAME}{API_SYSTEM_INFO}", json={"firmware_version": "2.20.1"})
    aioclient_mock.get(f"{FRAME}{API_BATTERY}", json={"percentage": 80, "voltage": 3.9})
    aioclient_mock.get(f"{FRAME}{API_SENSOR}", status=404)
    aioclient_mock.get(f"{FRAME}{API_CONFIG}", json={})
    aioclient_mock.get(f"{FRAME}{API_PROCESSING_SETTINGS}", json={})
    aioclient_mock.get(f"{FRAME}{API_OTA_STATUS}", json={"state": "idle"})
    aioclient_mock.get(f"{FRAME}{API_CURRENT_IMAGE}", status=404)

    coordinator = PhotoFrameCoordinator(hass, entry)
    await coordinator.async_refresh()

    assert aioclient_mock.mock_calls, "the refresh made no requests"
    for method, url, data, headers in aioclient_mock.mock_calls:
        assert str(url).startswith(f"{FRAME}/"), f"{url} is not the frame"
        assert (headers or {}).get("Authorization") == AUTH, f"{url} went out unauthenticated"


async def test_the_authed_session_only_recognises_the_frame(hass, entry):
    """Whatever a future call site asks of coordinator.session, the header stays home."""
    session = PhotoFrameCoordinator(hass, entry).session

    assert session.is_frame_url(FRAME)
    assert session.is_frame_url(f"{FRAME}/api/config")
    for url in (
        GITHUB,
        "https://example.com/",
        "http://192.168.1.50.example.com/api/config",
        "http://192.168.1.50:8080/api/config",
        "https://192.168.1.50/api/config",
    ):
        assert not session.is_frame_url(url), url


async def test_no_password_means_no_header(hass, aioclient_mock):
    """An open frame (the firmware default) is spoken to without any Authorization."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: FRAME}, entry_id="open")
    entry.add_to_hass(hass)
    aioclient_mock.get(f"{FRAME}{API_CONFIG}", json={})

    coordinator = PhotoFrameCoordinator(hass, entry)
    await coordinator._fetch_config()

    assert "Authorization" not in _headers_of(aioclient_mock, f"{FRAME}{API_CONFIG}")
