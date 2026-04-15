"""Text platform for ESP32 PhotoFrame."""

from __future__ import annotations

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PendingConfigEntityMixin, PhotoFrameCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the text platform."""
    coordinator: PhotoFrameCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        PhotoFrameImageUrlText(coordinator, entry),
        PhotoFrameHaUrlText(coordinator, entry),
    ]

    async_add_entities(entities)


class PhotoFrameImageUrlText(PendingConfigEntityMixin, CoordinatorEntity, TextEntity):
    """Image URL text entity for PhotoFrame."""

    _attr_has_entity_name = True
    _attr_available = True  # Always editable, even when device is offline
    _config_key = "image_url"
    _default_icon = "mdi:link"

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_image_url"
        self._attr_name = "Image URL"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> str | None:
        """Return the current image URL."""
        config = self.coordinator.data.get("config", {})
        return config.get("image_url", "")

    async def async_set_value(self, value: str) -> None:
        """Set the image URL."""
        await self.coordinator.async_set_config({"image_url": value})


class PhotoFrameHaUrlText(PendingConfigEntityMixin, CoordinatorEntity, TextEntity):
    """Home Assistant URL text entity for PhotoFrame."""

    _attr_has_entity_name = True
    _attr_available = True  # Always editable, even when device is offline
    _config_key = "ha_url"
    _default_icon = "mdi:home-assistant"

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_ha_url"
        self._attr_name = "Home Assistant URL"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> str | None:
        """Return the current HA URL."""
        config = self.coordinator.data.get("config", {})
        return config.get("ha_url", "")

    async def async_set_value(self, value: str) -> None:
        """Set the HA URL."""
        await self.coordinator.async_set_config({"ha_url": value})
