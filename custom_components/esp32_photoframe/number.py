"""Number platform for ESP32 PhotoFrame."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import (
    PendingConfigEntityMixin,
    PhotoFrameCoordinator,
    ProcessingSettingEntityMixin,
)


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
        PhotoFrameExposureNumber(coordinator, entry),
        PhotoFrameSaturationNumber(coordinator, entry),
        PhotoFrameContrastNumber(coordinator, entry),
        PhotoFrameScurveStrengthNumber(coordinator, entry),
        PhotoFrameScurveShadowBoostNumber(coordinator, entry),
        PhotoFrameScurveHighlightCompressNumber(coordinator, entry),
        PhotoFrameScurveMidpointNumber(coordinator, entry),
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


class PhotoFrameProcessingNumber(ProcessingSettingEntityMixin, CoordinatorEntity, NumberEntity):
    """Number backed by one field of the device's processing settings.

    Registry-disabled by default: these are image-tuning parameters most
    installs set once in the web UI. Firmware that predates the field, or a
    sleeping device, leaves the entity unavailable.
    """

    _attr_has_entity_name = True
    _attr_entity_registry_enabled_default = False
    _attr_mode = NumberMode.SLIDER
    _attr_native_step = 0.01
    _unique_suffix: str
    _default: float

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the number."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{self._unique_suffix}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        value = self._processing_settings.get(self._setting_key, self._default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return self._default

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        await self.coordinator.async_set_processing_settings({self._setting_key: value})


class PhotoFrameExposureNumber(PhotoFrameProcessingNumber):
    """Exposure multiplier for PhotoFrame image processing."""

    _attr_native_min_value = 0.5
    _attr_native_max_value = 2.0
    _attr_icon = "mdi:white-balance-sunny"
    _attr_name = "Exposure"
    _setting_key = "exposure"
    _unique_suffix = "proc_exposure"
    _default = 1.0


class PhotoFrameSaturationNumber(PhotoFrameProcessingNumber):
    """Saturation multiplier for PhotoFrame image processing."""

    # The grayscale preset stores 0.0, below the web UI's slider floor
    _attr_native_min_value = 0.0
    _attr_native_max_value = 2.0
    _attr_icon = "mdi:palette-outline"
    _attr_name = "Saturation"
    _setting_key = "saturation"
    _unique_suffix = "proc_saturation"
    _default = 1.0


class PhotoFrameContrastNumber(PhotoFrameProcessingNumber):
    """Contrast for PhotoFrame image processing (contrast tone mode)."""

    _attr_native_min_value = 0.5
    _attr_native_max_value = 2.0
    _attr_icon = "mdi:contrast-box"
    _attr_name = "Contrast"
    _setting_key = "contrast"
    _unique_suffix = "proc_contrast"
    _default = 1.0


class PhotoFrameScurveStrengthNumber(PhotoFrameProcessingNumber):
    """S-curve strength for PhotoFrame image processing."""

    _attr_native_min_value = 0.0
    _attr_native_max_value = 1.0
    _attr_icon = "mdi:chart-bell-curve"
    _attr_name = "S-curve strength"
    _setting_key = "strength"
    _unique_suffix = "proc_strength"
    _default = 0.5


class PhotoFrameScurveShadowBoostNumber(PhotoFrameProcessingNumber):
    """S-curve shadow boost for PhotoFrame image processing."""

    _attr_native_min_value = 0.0
    _attr_native_max_value = 1.0
    _attr_icon = "mdi:brightness-4"
    _attr_name = "S-curve shadow boost"
    _setting_key = "shadowBoost"
    _unique_suffix = "proc_shadow_boost"
    _default = 0.0


class PhotoFrameScurveHighlightCompressNumber(PhotoFrameProcessingNumber):
    """S-curve highlight compression for PhotoFrame image processing."""

    # The firmware default is 0.0 (contrast tone mode), below the web UI's
    # s-curve slider floor of 0.5
    _attr_native_min_value = 0.0
    _attr_native_max_value = 5.0
    _attr_icon = "mdi:brightness-7"
    _attr_name = "S-curve highlight compress"
    _setting_key = "highlightCompress"
    _unique_suffix = "proc_highlight_compress"
    _default = 0.0


class PhotoFrameScurveMidpointNumber(PhotoFrameProcessingNumber):
    """S-curve midpoint for PhotoFrame image processing."""

    _attr_native_min_value = 0.3
    _attr_native_max_value = 0.7
    _attr_icon = "mdi:circle-half-full"
    _attr_name = "S-curve midpoint"
    _setting_key = "midpoint"
    _unique_suffix = "proc_midpoint"
    _default = 0.5
