"""Image serving view for ESP32 PhotoFrame."""

from __future__ import annotations

import logging

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant

from .const import DOMAIN, IMAGE_ENDPOINT_PATH
from .coordinator import PhotoFrameCoordinator

_LOGGER = logging.getLogger(__name__)


def should_rotate(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Return whether the frame should rotate on this wake.

    Gated by the configured binary_sensor ("Auto rotate enabled sensor"): the
    frame rotates only while that sensor is on. No sensor configured, or a
    sensor that is missing/unavailable/unknown, defaults to rotating so a
    misconfiguration never freezes the frame — the device itself fail-closes
    only when it can't reach HA at all. For richer conditions, users point
    this at a Template binary-sensor helper.
    """
    entity_id = (entry.options.get("rotate_sensor") or "").strip()
    if not entity_id:
        return True
    state = hass.states.get(entity_id)
    if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
        _LOGGER.warning("Rotation-gate sensor %s unavailable; allowing rotation", entity_id)
        return True
    return state.state == "on"


def find_coordinator_by_device_id(
    hass: HomeAssistant, device_id: str
) -> PhotoFrameCoordinator | None:
    """Find coordinator matching the device ID.

    Args:
        hass: Home Assistant instance
        device_id: Unique ID of the device (MAC address)

    Returns:
        Matching coordinator or None if not found
    """
    for entry_id, coord in hass.data.get(DOMAIN, {}).items():
        # Get device ID from config entry
        coord_device_id = coord.entry.data.get("device_id")
        if coord_device_id == device_id:
            _LOGGER.debug(
                "Found matching coordinator for device ID '%s' (host: %s)",
                device_id,
                coord.host,
            )
            return coord

    available_ids = [
        coord.entry.data.get("device_id")
        for coord in hass.data.get(DOMAIN, {}).values()
        if hasattr(coord, "entry")
    ]
    _LOGGER.warning(
        "No coordinator found for device ID '%s' (available: %s)",
        device_id,
        available_ids,
    )
    return None


class PhotoFrameImageView(HomeAssistantView):
    """View to serve images to the photoframe."""

    url = IMAGE_ENDPOINT_PATH
    name = "api:esp32_photoframe:image"
    requires_auth = False  # Photoframe doesn't support auth

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the view."""
        self.hass = hass

    async def get(self, request: web.Request) -> web.Response:
        """Serve the configured image."""
        # Get the configured media entity from integration data
        # For now, we'll look for a configured entity in the integration options

        # Try to find the first photoframe integration
        photoframe_entries = [entry for entry in self.hass.config_entries.async_entries(DOMAIN)]

        if not photoframe_entries:
            _LOGGER.error("No PhotoFrame integration configured")
            return web.Response(status=404, text="No PhotoFrame integration configured")

        # Get the first entry's options
        entry = photoframe_entries[0]
        options = entry.options or {}

        # Get the configured media entity
        media_entity_id = options.get("media_entity_id")

        if not media_entity_id:
            _LOGGER.warning("No media entity configured for PhotoFrame image serving")
            return web.Response(status=404, text="No media entity configured")

        # Get the entity state
        state = self.hass.states.get(media_entity_id)
        if state is None:
            _LOGGER.error("Media entity %s not found", media_entity_id)
            return web.Response(status=404, text=f"Entity {media_entity_id} not found")

        # Handle different entity types
        if state.domain == "camera":
            # Get camera image
            from homeassistant.components.camera import async_get_image

            try:
                image = await async_get_image(self.hass, media_entity_id)
                return web.Response(
                    body=image.content,
                    content_type=image.content_type,
                    headers={
                        "Cache-Control": "no-cache, no-store, must-revalidate",
                        "Pragma": "no-cache",
                        "Expires": "0",
                    },
                )
            except Exception as err:
                _LOGGER.error("Error getting image from camera %s: %s", media_entity_id, err)
                return web.Response(status=500, text=f"Error getting image: {err}")

        elif state.domain == "image":
            # Get image entity's image
            try:
                # Image entities store their image URL in entity_picture attribute
                entity_picture = state.attributes.get("entity_picture")
                if not entity_picture:
                    return web.Response(status=404, text="Image entity has no picture")

                # Fetch the image from the entity_picture URL
                from homeassistant.helpers.aiohttp_client import async_get_clientsession

                session = async_get_clientsession(self.hass)

                # Build full URL if it's a relative path
                if entity_picture.startswith("/"):
                    # It's a local URL, fetch from HA
                    base_url = (
                        self.hass.config.external_url
                        or self.hass.config.internal_url
                        or "http://localhost:8123"
                    )
                    full_url = f"{base_url}{entity_picture}"
                else:
                    full_url = entity_picture

                async with session.get(full_url) as response:
                    if response.status != 200:
                        return web.Response(status=response.status, text="Failed to fetch image")

                    image_data = await response.read()
                    content_type = response.headers.get("Content-Type", "image/jpeg")

                    return web.Response(
                        body=image_data,
                        content_type=content_type,
                        headers={
                            "Cache-Control": "no-cache, no-store, must-revalidate",
                            "Pragma": "no-cache",
                            "Expires": "0",
                        },
                    )
            except Exception as err:
                _LOGGER.error("Error getting image from entity %s: %s", media_entity_id, err)
                return web.Response(status=500, text=f"Error getting image: {err}")

        else:
            _LOGGER.error("Entity %s is not a camera or image entity", media_entity_id)
            return web.Response(
                status=400,
                text=f"Entity {media_entity_id} is not a camera or image entity",
            )


class PhotoFrameNotifyView(HomeAssistantView):
    """View to receive simple notification from photoframe to trigger data refresh."""

    url = "/api/esp32_photoframe/notify"
    name = "api:esp32_photoframe:notify"
    requires_auth = False  # Photoframe doesn't support auth

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the view."""
        self.hass = hass

    async def post(self, request: web.Request) -> web.Response:
        """Receive notification from photoframe and trigger coordinator refresh."""
        try:
            # Parse JSON body
            try:
                data = await request.json()
                device_id = data.get("device_id")
                device_name = data.get("device_name", "Unknown")
                state = data.get("state", "online")
            except Exception as err:
                _LOGGER.error("Failed to parse JSON notification: %s", err)
                return web.Response(status=400, text="Invalid JSON payload")

            if not device_id:
                _LOGGER.error("Missing device_id in notification")
                return web.Response(status=400, text="Missing device_id")

            _LOGGER.info(
                "Received %s notification from device '%s' (ID: %s)",
                state,
                device_name,
                device_id,
            )

            # Find the coordinator that matches this device ID
            coordinator = find_coordinator_by_device_id(self.hass, device_id)
            if not coordinator:
                return web.Response(status=404, text="Device not found")

            if state == "offline":
                # Mark device as offline
                _LOGGER.info("Device %s going offline (deep sleep)", device_name)
                coordinator._device_online = False
                coordinator.async_set_updated_data(coordinator.data)
            elif state == "update":
                # Device has new data - trigger coordinator refresh to fetch updated data
                _LOGGER.info(
                    "Device %s has updates, triggering coordinator refresh",
                    device_name,
                )
                coordinator._device_online = True
                # Push any pending config changes now that the device webserver is up
                self.hass.async_create_task(coordinator.async_push_pending_config())
                # Schedule refresh in background to avoid blocking HTTP response
                self.hass.async_create_task(coordinator.async_request_refresh())
                _LOGGER.info("Coordinator refresh scheduled")
            else:
                # Device is online - push pending config and refresh to pick up
                # any changes the user may have made via the device web UI
                _LOGGER.info("Device %s is online", device_name)
                coordinator._device_online = True
                self.hass.async_create_task(coordinator.async_push_pending_config())
                self.hass.async_create_task(coordinator.async_request_refresh())

            # Answer the device's rotation-gate question (piggybacked on the
            # online notification): { "rotate": true|false }.
            rotate = should_rotate(self.hass, coordinator.entry)
            return web.json_response({"rotate": rotate})
        except Exception as err:
            _LOGGER.error("Error processing notification: %s", err)
            return web.Response(status=400, text=f"Error: {err}")


async def async_setup_image_view(hass: HomeAssistant) -> None:
    """Set up the image serving view."""
    hass.http.register_view(PhotoFrameImageView(hass))
    hass.http.register_view(PhotoFrameNotifyView(hass))
    _LOGGER.info("Registered PhotoFrame image serving endpoint at %s", IMAGE_ENDPOINT_PATH)
    _LOGGER.info("Registered PhotoFrame notify endpoint at /api/esp32_photoframe/notify")
