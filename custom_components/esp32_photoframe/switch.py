"""Switch platform for ESP32 PhotoFrame."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.network import get_url
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_HA_URL, DOMAIN, IMAGE_ENDPOINT_PATH
from .coordinator import PendingConfigEntityMixin, PhotoFrameCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    coordinator: PhotoFrameCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        PhotoFrameAutoRotateSwitch(coordinator, entry),
        PhotoFrameDeepSleepSwitch(coordinator, entry),
        PhotoFrameUseHAImagesSwitch(coordinator, entry, hass),
        PhotoFrameSleepScheduleSwitch(coordinator, entry),
    ]

    async_add_entities(entities)


class PhotoFrameAutoRotateSwitch(
    PendingConfigEntityMixin, CoordinatorEntity, SwitchEntity
):
    """Auto-rotate switch for PhotoFrame."""

    _attr_has_entity_name = True
    _attr_available = True  # Always editable, even when device is offline
    _config_key = "auto_rotate"
    _default_icon = "mdi:rotate-3d-variant"

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_auto_rotate"
        self._attr_name = "Auto rotate"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool:
        """Return true if auto-rotate is on."""
        config = self.coordinator.data.get("config", {})
        return config.get("auto_rotate", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on auto-rotate."""
        await self.coordinator.async_set_config({"auto_rotate": True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off auto-rotate."""
        await self.coordinator.async_set_config({"auto_rotate": False})


class PhotoFrameDeepSleepSwitch(
    PendingConfigEntityMixin, CoordinatorEntity, SwitchEntity
):
    """Deep sleep switch for PhotoFrame."""

    _attr_has_entity_name = True
    _attr_available = True  # Always editable, even when device is offline
    _config_key = "deep_sleep_enabled"
    _default_icon = "mdi:sleep"

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_deep_sleep"
        self._attr_name = "Deep sleep"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool:
        """Return true if deep sleep is enabled."""
        config = self.coordinator.data.get("config", {})
        return config.get("deep_sleep_enabled", True)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable deep sleep."""
        await self.coordinator.async_set_config({"deep_sleep_enabled": True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable deep sleep."""
        await self.coordinator.async_set_config({"deep_sleep_enabled": False})


class PhotoFrameUseHAImagesSwitch(CoordinatorEntity, SwitchEntity):
    """Use HA Images switch for PhotoFrame."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:home-assistant"
    _attr_available = True  # Always editable, even when device is offline

    def __init__(
        self,
        coordinator: PhotoFrameCoordinator,
        entry: ConfigEntry,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_use_ha_images"
        self._attr_name = "Use HA images"
        self._attr_device_info = coordinator.device_info
        self._entry = entry
        self._hass = hass

    @property
    def is_on(self) -> bool:
        """Return true if HA image serving is enabled."""
        return self._entry.options.get("use_ha_images", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable HA image serving."""
        new_options = dict(self._entry.options)
        new_options["use_ha_images"] = True
        self._hass.config_entries.async_update_entry(self._entry, options=new_options)
        self.async_write_ha_state()

        # Push image URL to device (cached if offline)
        ha_url = self._entry.data.get(CONF_HA_URL) or get_url(self._hass)
        image_url = f"{ha_url}{IMAGE_ENDPOINT_PATH}"
        await self.coordinator.async_set_config({"image_url": image_url})
        _LOGGER.info("Configured photoframe to use HA images: %s", image_url)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable HA image serving."""
        new_options = dict(self._entry.options)
        new_options["use_ha_images"] = False
        self._hass.config_entries.async_update_entry(self._entry, options=new_options)
        self.async_write_ha_state()
        _LOGGER.info("Disabled HA image serving - photoframe will use configured URL")


class PhotoFrameSleepScheduleSwitch(
    PendingConfigEntityMixin, CoordinatorEntity, SwitchEntity
):
    """Sleep schedule switch for PhotoFrame."""

    _attr_has_entity_name = True
    _attr_available = True  # Always editable, even when device is offline
    _config_key = "sleep_schedule_enabled"
    _default_icon = "mdi:sleep"

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_sleep_schedule"
        self._attr_name = "Sleep schedule"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool:
        """Return true if sleep schedule is enabled."""
        config = self.coordinator.data.get("config", {})
        return config.get("sleep_schedule_enabled", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable sleep schedule."""
        await self.coordinator.async_set_config({"sleep_schedule_enabled": True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable sleep schedule."""
        await self.coordinator.async_set_config({"sleep_schedule_enabled": False})
