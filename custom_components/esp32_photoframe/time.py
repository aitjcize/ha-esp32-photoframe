"""Time platform for ESP32 PhotoFrame."""

from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
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
    """Set up the time platform."""
    coordinator: PhotoFrameCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        PhotoFrameSleepScheduleStartTime(coordinator, entry),
        PhotoFrameSleepScheduleEndTime(coordinator, entry),
    ]

    async_add_entities(entities)


class PhotoFrameSleepScheduleStartTime(PendingConfigEntityMixin, CoordinatorEntity, TimeEntity):
    """Sleep schedule start time for PhotoFrame."""

    _attr_has_entity_name = True
    _attr_available = True  # Always editable, even when device is offline
    _config_key = "sleep_schedule_start"
    _default_icon = "mdi:sleep"

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the time entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_sleep_schedule_start"
        self._attr_name = "Sleep schedule start"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> time | None:
        """Return the current sleep schedule start time."""
        config = self.coordinator.data.get("config", {})
        minutes = config.get("sleep_schedule_start", 0)
        hours = minutes // 60
        mins = minutes % 60
        return time(hour=hours, minute=mins)

    async def async_set_value(self, value: time) -> None:
        """Set the sleep schedule start time."""
        minutes = value.hour * 60 + value.minute
        await self.coordinator.async_set_config({"sleep_schedule_start": minutes})


class PhotoFrameSleepScheduleEndTime(PendingConfigEntityMixin, CoordinatorEntity, TimeEntity):
    """Sleep schedule end time for PhotoFrame."""

    _attr_has_entity_name = True
    _attr_available = True  # Always editable, even when device is offline
    _config_key = "sleep_schedule_end"
    _default_icon = "mdi:sleep-off"

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the time entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_sleep_schedule_end"
        self._attr_name = "Sleep schedule end"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> time | None:
        """Return the current sleep schedule end time."""
        config = self.coordinator.data.get("config", {})
        minutes = config.get("sleep_schedule_end", 0)
        hours = minutes // 60
        mins = minutes % 60
        return time(hour=hours, minute=mins)

    async def async_set_value(self, value: time) -> None:
        """Set the sleep schedule end time."""
        minutes = value.hour * 60 + value.minute
        await self.coordinator.async_set_config({"sleep_schedule_end": minutes})
