"""The image view serves a frame only through that frame's secret URL.

The frame cannot authenticate to Home Assistant, so the view used to serve the
configured camera to anyone who could reach Home Assistant, including from the
internet (ha-esp32-photoframe#12). Each frame now fetches
/api/esp32_photoframe/image/<token>, gets its own media entity, and is
refused while "Use HA images" is off or, by default, from outside the LAN.
"""

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.esp32_photoframe.const import (
    CONF_HA_URL,
    CONF_HOST,
    CONF_IMAGE_LOCAL_ONLY,
    CONF_IMAGE_TOKEN,
    DOMAIN,
    IMAGE_ENDPOINT_PATH,
)
from custom_components.esp32_photoframe.image_endpoint import (
    async_ensure_image_token,
    async_track_image_url,
    ha_image_url,
    is_ha_image_url,
)
from custom_components.esp32_photoframe.view import PhotoFrameImageView, _is_local_request

HA_URL = "http://192.168.1.10:8123"
LEGACY_URL = f"{HA_URL}{IMAGE_ENDPOINT_PATH}"


def _frame(hass, entry_id, token, camera, **options):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=entry_id,
        entry_id=entry_id,
        data={CONF_HOST: "http://192.168.1.50", CONF_HA_URL: HA_URL, CONF_IMAGE_TOKEN: token},
        options={"use_ha_images": True, "media_entity_id": camera, **options},
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
async def client(hass, hass_client_no_auth):
    """An HTTP client against the image view, with two frames on two cameras."""
    assert await async_setup_component(hass, "http", {})
    hass.http.register_view(PhotoFrameImageView(hass))
    hass.states.async_set("camera.front", "idle")
    hass.states.async_set("camera.back", "idle")
    return await hass_client_no_auth()


def _camera_image(hass, entity_id):
    return SimpleNamespace(content=entity_id.encode(), content_type="image/jpeg")


@pytest.fixture(autouse=True)
def camera_images():
    # A stand-in for homeassistant.components.camera, whose real import needs
    # turbojpeg; the view imports async_get_image from it at request time
    camera = ModuleType("homeassistant.components.camera")
    camera.async_get_image = AsyncMock(side_effect=_camera_image)
    with patch.dict(sys.modules, {"homeassistant.components.camera": camera}):
        yield


async def test_each_token_serves_its_own_frame(hass, client):
    _frame(hass, "living", "tok-living", "camera.front")
    _frame(hass, "bedroom", "tok-bedroom", "camera.back")

    resp = await client.get(f"{IMAGE_ENDPOINT_PATH}/tok-living")
    assert resp.status == 200
    assert await resp.read() == b"camera.front"

    resp = await client.get(f"{IMAGE_ENDPOINT_PATH}/tok-bedroom")
    assert resp.status == 200
    assert await resp.read() == b"camera.back"


@pytest.mark.parametrize("path", ["", "/", "/wrong-token", "/tok-living-x"])
async def test_no_image_without_the_right_token(hass, client, path):
    _frame(hass, "living", "tok-living", "camera.front")

    resp = await client.get(f"{IMAGE_ENDPOINT_PATH}{path}")
    assert resp.status == 404
    assert await resp.read() != b"camera.front"


async def test_no_image_while_use_ha_images_is_off(hass, client):
    _frame(hass, "living", "tok-living", "camera.front", use_ha_images=False)

    resp = await client.get(f"{IMAGE_ENDPOINT_PATH}/tok-living")
    assert resp.status == 404


async def test_remote_requests_refused_unless_allowed(hass, client):
    entry = _frame(hass, "living", "tok-living", "camera.front")

    with patch("custom_components.esp32_photoframe.view._is_local_request", return_value=False):
        resp = await client.get(f"{IMAGE_ENDPOINT_PATH}/tok-living")
        assert resp.status == 404

        hass.config_entries.async_update_entry(
            entry, options={**entry.options, CONF_IMAGE_LOCAL_ONLY: False}
        )
        resp = await client.get(f"{IMAGE_ENDPOINT_PATH}/tok-living")
        assert resp.status == 200


@pytest.mark.parametrize(
    ("remote", "cloud", "local"),
    [
        ("192.168.1.50", False, True),
        ("10.0.0.7", False, True),
        ("127.0.0.1", False, True),
        ("fe80::1", False, True),
        ("203.0.113.5", False, False),
        ("2001:db8::1", False, False),
        ("127.0.0.1", True, False),  # relayed by Home Assistant Cloud
        (None, False, False),
        ("not-an-ip", False, False),
    ],
)
def test_is_local_request(hass, remote, cloud, local):
    with patch("custom_components.esp32_photoframe.view.is_cloud_connection", return_value=cloud):
        assert _is_local_request(hass, SimpleNamespace(remote=remote)) is local


async def test_token_is_created_once(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: "http://192.168.1.50", CONF_HA_URL: HA_URL}
    )
    entry.add_to_hass(hass)

    token = async_ensure_image_token(hass, entry)
    assert len(token) == 32
    assert entry.data[CONF_IMAGE_TOKEN] == token
    assert async_ensure_image_token(hass, entry) == token
    assert ha_image_url(hass, entry) == f"{HA_URL}{IMAGE_ENDPOINT_PATH}/{token}"


def test_is_ha_image_url():
    assert is_ha_image_url(LEGACY_URL)
    assert is_ha_image_url(f"{LEGACY_URL}/")
    assert is_ha_image_url(f"{LEGACY_URL}/abc")
    assert not is_ha_image_url("https://photos.example.com/next.jpg")
    assert not is_ha_image_url(f"{HA_URL}/api/esp32_photoframe/images")
    assert not is_ha_image_url("")
    assert not is_ha_image_url(None)
    assert not is_ha_image_url("http://[::1/image")


class FakeCoordinator:
    """Just the coordinator surface the URL tracking and the switch use."""

    def __init__(self, image_url):
        self.data = {"config": {"image_url": image_url}}
        self._listeners = []
        self.async_set_config = AsyncMock(side_effect=self._set_config)

    async def _set_config(self, config):
        self.data = {**self.data, "config": {**self.data["config"], **config}}
        for listener in list(self._listeners):
            listener()
        return True

    def async_add_listener(self, listener):
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)


@pytest.mark.parametrize(
    ("current", "use_ha_images", "expected"),
    [
        # Set up by an older release: the token path, on the frame's own address
        (LEGACY_URL, True, f"{HA_URL}{IMAGE_ENDPOINT_PATH}/tok-living"),
        (f"{LEGACY_URL}/old-token", True, f"{HA_URL}{IMAGE_ENDPOINT_PATH}/tok-living"),
        (
            f"https://ha.example.com{IMAGE_ENDPOINT_PATH}?x=1",
            True,
            f"https://ha.example.com{IMAGE_ENDPOINT_PATH}/tok-living",
        ),
        # Already on its token, at whatever address the user gave it
        (f"{HA_URL}{IMAGE_ENDPOINT_PATH}/tok-living", True, None),
        (f"https://ha.example.com{IMAGE_ENDPOINT_PATH}/tok-living", True, None),
        ("https://photos.example.com/next.jpg", True, None),  # the user's own server
        ("http://[::1/image", True, None),  # malformed
        (LEGACY_URL, False, None),  # HA images off: not ours to change
        ("", True, None),  # config not known yet
    ],
)
async def test_frames_are_moved_to_their_token_url(hass, current, use_ha_images, expected):
    entry = _frame(hass, "living", "tok-living", "camera.front", use_ha_images=use_ha_images)
    coordinator = FakeCoordinator(current)

    async_track_image_url(hass, entry, coordinator)
    await hass.async_block_till_done()

    if expected:
        coordinator.async_set_config.assert_awaited_once_with({"image_url": expected})
    else:
        coordinator.async_set_config.assert_not_awaited()


async def test_migration_waits_for_the_frame_config(hass):
    entry = _frame(hass, "living", "tok-living", "camera.front")
    coordinator = FakeCoordinator("")
    coordinator.data = None  # frame asleep, nothing cached

    async_track_image_url(hass, entry, coordinator)
    await hass.async_block_till_done()
    coordinator.async_set_config.assert_not_awaited()

    # The frame wakes and its config arrives
    coordinator.data = {"config": {"image_url": LEGACY_URL}}
    for listener in list(coordinator._listeners):
        listener()
    await hass.async_block_till_done()
    coordinator.async_set_config.assert_awaited_once_with(
        {"image_url": f"{HA_URL}{IMAGE_ENDPOINT_PATH}/tok-living"}
    )
