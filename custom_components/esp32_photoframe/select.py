"""Select platform for ESP32 PhotoFrame."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
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
    """Set up the select platform."""
    coordinator: PhotoFrameCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        PhotoFrameRotationModeSelect(coordinator, entry),
        PhotoFrameMediaEntitySelect(coordinator, entry, hass),
        PhotoFrameDisplayOrientationSelect(coordinator, entry),
    ]

    async_add_entities(entities)


class PhotoFrameRotationModeSelect(PendingConfigEntityMixin, CoordinatorEntity, SelectEntity):
    """Rotation mode select for PhotoFrame."""

    _attr_has_entity_name = True
    _attr_available = True  # Always editable, even when device is offline
    _config_key = "rotation_mode"
    _default_icon = "mdi:image-multiple"

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the select."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_rotation_mode"
        self._attr_name = "Rotation mode"
        self._attr_device_info = coordinator.device_info

    @property
    def options(self) -> list[str]:
        """Return available rotation modes."""
        if not self.coordinator.has_storage:
            return ["url"]
        return ["storage", "url"]

    @property
    def current_option(self) -> str | None:
        """Return the current rotation mode."""
        config = self.coordinator.data.get("config", {})
        mode = config.get("rotation_mode", "storage")
        # Backwards compatibility: old firmware returns "sdcard"
        if mode == "sdcard":
            mode = "storage"
        return mode

    async def async_select_option(self, option: str) -> None:
        """Set the rotation mode."""
        await self.coordinator.async_set_config({"rotation_mode": option})


class PhotoFrameMediaEntitySelect(CoordinatorEntity, SelectEntity):
    """Media entity select for PhotoFrame image serving."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:camera"
    _attr_available = True  # Always editable, even when device is offline

    def __init__(
        self,
        coordinator: PhotoFrameCoordinator,
        entry: ConfigEntry,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the select."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_media_entity"
        self._attr_name = "Media source"
        self._attr_device_info = coordinator.device_info
        self._hass = hass
        self._entry = entry

    @property
    def options(self) -> list[str]:
        """Return available camera and image entities."""
        from homeassistant.helpers import entity_registry as er

        entity_reg = er.async_get(self._hass)
        camera_entities = [
            entity.entity_id
            for entity in entity_reg.entities.values()
            if entity.domain in ("camera", "image")
        ]

        # Add state-based entities as well
        for state in self._hass.states.async_all():
            if state.domain in ("camera", "image") and state.entity_id not in camera_entities:
                camera_entities.append(state.entity_id)

        camera_entities.sort()
        return ["None"] + camera_entities

    @property
    def current_option(self) -> str | None:
        """Return the currently selected media entity."""
        return self._entry.options.get("media_entity_id") or "None"

    async def async_select_option(self, option: str) -> None:
        """Set the media entity."""
        # Update the config entry options
        new_options = dict(self._entry.options)
        new_options["media_entity_id"] = option if option != "None" else ""

        self._hass.config_entries.async_update_entry(self._entry, options=new_options)

        # Force state update
        self.async_write_ha_state()


class PhotoFrameDisplayOrientationSelect(PendingConfigEntityMixin, CoordinatorEntity, SelectEntity):
    """Display orientation select for PhotoFrame."""

    _attr_has_entity_name = True
    _attr_options = ["landscape", "portrait"]
    _attr_available = True  # Always editable, even when device is offline
    _config_key = "display_orientation"
    _default_icon = "mdi:phone-rotate-landscape"

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the select."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_display_orientation"
        self._attr_name = "Display orientation"
        self._attr_device_info = coordinator.device_info

    @property
    def current_option(self) -> str | None:
        """Return the current display orientation."""
        config = self.coordinator.data.get("config", {})
        return config.get("display_orientation", "landscape")

    async def async_select_option(self, option: str) -> None:
        """Set the display orientation."""
        await self.coordinator.async_set_config({"display_orientation": option})
