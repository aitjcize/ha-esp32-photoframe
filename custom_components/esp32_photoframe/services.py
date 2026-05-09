"""Services for ESP32 PhotoFrame integration."""

from __future__ import annotations

import logging

import aiohttp
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, SERVICE_DISPLAY_IMAGE, SERVICE_ROTATE
from .coordinator import PhotoFrameCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_DISPLAY_IMAGE_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
    }
)


async def async_register_services(hass: HomeAssistant, coordinator: PhotoFrameCoordinator) -> None:
    """Register services for the integration."""

    async def handle_rotate(call: ServiceCall) -> None:
        """Handle the rotate service call."""
        try:
            async with coordinator.session.post(
                f"{coordinator.host}/api/rotate",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    _LOGGER.info("Successfully triggered image rotation")
                    await coordinator.async_request_refresh()
                else:
                    _LOGGER.error("Failed to trigger rotation: HTTP %s", response.status)
        except aiohttp.ClientError as err:
            _LOGGER.error("Failed to trigger rotation: %s", err)

    async def handle_display_image(call: ServiceCall) -> None:
        """Handle the display_image service call."""
        entity_id = call.data["entity_id"]

        # Get the camera/image entity
        state = hass.states.get(entity_id)
        if state is None:
            _LOGGER.error("Entity %s not found", entity_id)
            return

        # For camera entities, get the image
        if state.domain == "camera":
            from homeassistant.components.camera import async_get_image

            try:
                image = await async_get_image(hass, entity_id)
                success = await coordinator.async_display_image(image.content)
                if success:
                    _LOGGER.info("Successfully displayed image from %s", entity_id)
                else:
                    _LOGGER.error("Failed to display image from %s", entity_id)
            except Exception as err:
                _LOGGER.error("Error getting image from %s: %s", entity_id, err)
        else:
            _LOGGER.error("Entity %s is not a camera", entity_id)

    hass.services.async_register(
        DOMAIN,
        SERVICE_ROTATE,
        handle_rotate,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_DISPLAY_IMAGE,
        handle_display_image,
        schema=SERVICE_DISPLAY_IMAGE_SCHEMA,
    )
