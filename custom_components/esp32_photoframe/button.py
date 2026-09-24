"""Button platform for ESP32 PhotoFrame."""

from __future__ import annotations

import asyncio
import logging

import aiohttp
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PhotoFrameCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    coordinator: PhotoFrameCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        PhotoFrameRotateButton(coordinator, entry),
        PhotoFrameRefreshButton(coordinator, entry),
        PhotoFrameSleepButton(coordinator, entry),
    ]

    async_add_entities(entities)


class PhotoFrameRotateButton(CoordinatorEntity, ButtonEntity):
    """Rotate button for PhotoFrame."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_rotate"
        self._attr_name = "Rotate image"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.available

    async def async_press(self) -> None:
        """Handle the button press."""
        # Fire and forget - don't wait for the HTTP request to complete
        # This prevents timeout errors when image rotation takes a long time
        asyncio.create_task(self._trigger_rotation())
        _LOGGER.info("Image rotation triggered (fire-and-forget)")

    async def _trigger_rotation(self) -> None:
        """Trigger rotation in the background."""
        try:
            url = f"{self.coordinator.host}/api/rotate"
            _LOGGER.debug("Sending POST request to %s", url)
            async with self.coordinator.session.post(
                url,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as response:
                response_text = await response.text()
                _LOGGER.debug(
                    "Rotation response: HTTP %s, body: %s",
                    response.status,
                    response_text,
                )
                if response.status == 200:
                    _LOGGER.info("Successfully completed image rotation")
                    await self.coordinator.async_request_refresh()
                else:
                    _LOGGER.error(
                        "Failed to trigger rotation: HTTP %s, response: %s",
                        response.status,
                        response_text,
                    )
        except aiohttp.ClientError as err:
            _LOGGER.error("Failed to trigger rotation (ClientError): %s", err)
        except Exception as err:
            _LOGGER.error("Failed to trigger rotation (unexpected error): %s", err, exc_info=True)


class PhotoFrameRefreshButton(CoordinatorEntity, ButtonEntity):
    """Refresh button to check device availability."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:refresh-circle"

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_refresh"
        self._attr_name = "Refresh status"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """Refresh button is always available."""
        return True

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.info("Manual refresh requested - checking device availability")
        await self.coordinator.async_request_refresh()


class PhotoFrameSleepButton(CoordinatorEntity, ButtonEntity):
    """Deep sleep button for PhotoFrame."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:sleep"

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_sleep"
        self._attr_name = "Enter deep sleep"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.available

    async def async_press(self) -> None:
        """Handle the button press."""
        # Fire and forget - device will go to sleep immediately
        asyncio.create_task(self._trigger_sleep())
        _LOGGER.info("Deep sleep triggered (fire-and-forget)")

    async def _trigger_sleep(self) -> None:
        """Trigger deep sleep in the background."""
        try:
            url = f"{self.coordinator.host}/api/sleep"
            _LOGGER.debug("Sending POST request to %s", url)
            async with self.coordinator.session.post(
                url,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response_text = await response.text()
                _LOGGER.debug("Sleep response: HTTP %s, body: %s", response.status, response_text)
                if response.status == 200:
                    _LOGGER.info("Device entering deep sleep")
                else:
                    _LOGGER.error(
                        "Failed to trigger sleep: HTTP %s, response: %s",
                        response.status,
                        response_text,
                    )
        except aiohttp.ClientError as err:
            _LOGGER.error("Failed to trigger sleep (ClientError): %s", err)
        except Exception as err:
            _LOGGER.error("Failed to trigger sleep (unexpected error): %s", err, exc_info=True)
