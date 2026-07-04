"""Number platform for ESP32 PhotoFrame."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PendingConfigEntityMixin, PhotoFrameCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the number platform."""
    coordinator: PhotoFrameCoordinator = hass.data[DOMAIN][entry.entry_id]

    # The rotation-interval number was replaced by the rotation-schedule text
    # entity; drop the stale registry entry so upgrades don't leave a
    # permanently-unavailable orphan behind.
    ent_reg = er.async_get(hass)
    stale = ent_reg.async_get_entity_id("number", DOMAIN, f"{entry.entry_id}_rotation_interval")
    if stale:
        ent_reg.async_remove(stale)

    entities = [
        PhotoFrameTimezoneOffsetNumber(coordinator, entry),
    ]

    async_add_entities(entities)


class PhotoFrameTimezoneOffsetNumber(PendingConfigEntityMixin, CoordinatorEntity, NumberEntity):
    """Timezone offset number for PhotoFrame."""

    _attr_has_entity_name = True
    _attr_native_min_value = -12
    _attr_native_max_value = 14
    _attr_native_step = 0.5
    _attr_mode = NumberMode.BOX
    _attr_available = True  # Always editable, even when device is offline
    _config_key = "timezone"
    _default_icon = "mdi:map-clock"

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the number."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_timezone_offset"
        self._attr_name = "Timezone offset"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> float | None:
        """Return the current timezone offset."""
        config = self.coordinator.data.get("config", {})
        timezone = config.get("timezone", "UTC0")

        # Parse POSIX format (e.g., "UTC-8" -> 8, "UTC+5:30" -> -5.5)
        import re

        match = re.match(r"UTC([+-]?)(\d+)(?::(\d+))?", timezone)
        if match:
            sign = 1 if match.group(1) == "-" else -1  # POSIX format is inverted
            hours = int(match.group(2) or 0)
            minutes = int(match.group(3) or 0)
            return sign * (hours + minutes / 60)
        return 0

    async def async_set_native_value(self, value: float) -> None:
        """Set the timezone offset (convert to POSIX format)."""
        # POSIX format is inverted: UTC-8 means 8 hours ahead
        if value == 0:
            timezone = "UTC0"
        else:
            abs_offset = abs(value)
            hours = int(abs_offset)
            minutes = int(round((abs_offset - hours) * 60))
            sign = "-" if value > 0 else "+"  # Inverted for POSIX

            if minutes == 0:
                timezone = f"UTC{sign}{hours}"
            else:
                timezone = f"UTC{sign}{hours}:{minutes:02d}"

        await self.coordinator.async_set_config({"timezone": timezone})
