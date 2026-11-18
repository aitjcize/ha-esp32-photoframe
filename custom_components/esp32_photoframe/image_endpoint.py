"""Per-frame URLs for the image Home Assistant serves to a frame.

The frame cannot log in to Home Assistant, so the image view has no HA
authentication. Instead every frame gets a random token in its image URL
(IMAGE_ENDPOINT_PATH/<token>); the view serves only a request whose token
matches a frame with "Use HA images" turned on.
"""

from __future__ import annotations

import logging
import secrets
from urllib.parse import urlsplit, urlunsplit

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.network import get_url

from .const import CONF_HA_URL, CONF_IMAGE_TOKEN, IMAGE_ENDPOINT_PATH

_LOGGER = logging.getLogger(__name__)

# 24 random bytes: a 32-character token, which keeps the whole URL well inside
# the frame's 255-character image URL
_TOKEN_BYTES = 24


@callback
def async_ensure_image_token(hass: HomeAssistant, entry: ConfigEntry) -> str:
    """Return the entry's image token, creating it on first use."""
    token = entry.data.get(CONF_IMAGE_TOKEN)
    if not token:
        token = secrets.token_urlsafe(_TOKEN_BYTES)
        hass.config_entries.async_update_entry(entry, data={**entry.data, CONF_IMAGE_TOKEN: token})
    return token


def _token_path(entry: ConfigEntry) -> str:
    return f"{IMAGE_ENDPOINT_PATH}/{entry.data[CONF_IMAGE_TOKEN]}"


def ha_image_url(hass: HomeAssistant, entry: ConfigEntry, base_url: str | None = None) -> str:
    """Return the image URL the frame should fetch while it uses HA images.

    base_url is the address the frame reaches Home Assistant at (its own Home
    Assistant URL setting); without one, the address saved at setup is used.
    """
    base = (base_url or entry.data.get(CONF_HA_URL) or get_url(hass)).rstrip("/")
    return f"{base}{_token_path(entry)}"


def _url_path(url: str | None) -> str | None:
    if not url:
        return None
    try:
        return urlsplit(url).path.rstrip("/")
    except ValueError:  # e.g. an unmatched IPv6 bracket
        return None


def is_ha_image_url(url: str | None) -> bool:
    """Return whether a URL points at this integration's image view."""
    path = _url_path(url)
    if path is None:
        return False
    return path == IMAGE_ENDPOINT_PATH or path.startswith(f"{IMAGE_ENDPOINT_PATH}/")


@callback
def async_track_image_url(hass: HomeAssistant, entry: ConfigEntry, coordinator) -> None:
    """Keep a frame that uses HA images on its own token URL.

    A frame set up by an older release fetches the bare endpoint, which serves
    nothing now. It is sent the token path on the same address as soon as its
    config is known (the change reaches a sleeping frame at its next wake,
    like any other config change). The address itself is the user's to set,
    so a URL that already carries the right token is left alone.
    """
    in_flight = False

    async def _async_push(url: str) -> None:
        nonlocal in_flight
        try:
            await coordinator.async_set_config({"image_url": url})
            _LOGGER.info("Sent %s its new Home Assistant image URL", entry.title)
        except HomeAssistantError as err:
            _LOGGER.warning("Could not update the image URL of %s: %s", entry.title, err)
        finally:
            in_flight = False

    @callback
    def _async_check() -> None:
        nonlocal in_flight
        if in_flight or not entry.options.get("use_ha_images"):
            return
        config = (coordinator.data or {}).get("config") or {}
        current = config.get("image_url")
        # Only ever replace a URL this integration set; a frame whose user
        # pointed it somewhere else keeps that URL
        if not is_ha_image_url(current) or _url_path(current) == _token_path(entry):
            return
        url = urlunsplit(urlsplit(current)._replace(path=_token_path(entry), query="", fragment=""))
        in_flight = True
        entry.async_create_background_task(hass, _async_push(url), f"{entry.entry_id}_image_url")

    entry.async_on_unload(coordinator.async_add_listener(_async_check))
    _async_check()
