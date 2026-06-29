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
        PhotoFrameRotationScheduleText(coordinator, entry),
        PhotoFrameImageUrlText(coordinator, entry),
        PhotoFrameHaUrlText(coordinator, entry),
    ]

    async_add_entities(entities)


class PhotoFrameRotationScheduleText(PendingConfigEntityMixin, CoordinatorEntity, TextEntity):
    """Rotation schedule (cron) text entity for PhotoFrame.

    The schedule is a list of simplified 3-field cron rules
    ("minute hour day-of-week"). Multiple rules are shown/edited as a single
    "; "-separated string, e.g. "0 */12 *" or "0 9 1-5; 0 18 0,6".
    """

    _attr_has_entity_name = True
    _attr_available = True  # Always editable, even when device is offline
    _attr_native_max = 255
    _config_key = "rotate_cron"
    _default_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_rotation_schedule"
        self._attr_name = "Rotation schedule"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> str | None:
        """Return the rotation schedule as a "; "-joined cron string."""
        config = self.coordinator.data.get("config", {})
        rules = config.get("rotate_cron") or []
        if isinstance(rules, str):
            rules = [rules]
        return "; ".join(str(r).strip() for r in rules if str(r).strip())

    async def async_set_value(self, value: str) -> None:
        """Set the rotation schedule from a "; "/newline-separated cron string."""
        rules = [r.strip() for r in value.replace("\n", ";").split(";")]
        rules = [r for r in rules if r]
        await self.coordinator.async_set_config({"rotate_cron": rules})


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
