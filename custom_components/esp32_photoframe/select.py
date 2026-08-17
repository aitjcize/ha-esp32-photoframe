"""Select platform for ESP32 PhotoFrame."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PendingConfigEntityMixin, PhotoFrameCoordinator
from .dynamic_entities import async_setup_firmware_gated_entities


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
        PhotoFrameScaleModeSelect(coordinator, entry),
        PhotoFrameFitBackgroundSelect(coordinator, entry),
        PhotoFrameRotateEnabledSensorSelect(coordinator, entry, hass),
    ]

    async_add_entities(entities)

    # Advanced network settings (#43): only firmware reporting ip_mode
    # supports static IP configuration.
    async_setup_firmware_gated_entities(
        hass,
        coordinator,
        async_add_entities,
        "select",
        "ip_mode",
        [lambda: PhotoFrameIpModeSelect(coordinator, entry)],
    )


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


class PhotoFrameScaleModeSelect(CoordinatorEntity, SelectEntity):
    """Photo scale mode (cover/fit) select for PhotoFrame.

    Backed by the device's processing settings (synced to the server via the
    X-Processing-Settings header), not the config endpoint, so changes need
    the device awake.
    """

    _attr_has_entity_name = True
    _attr_options = ["cover", "fit"]
    _attr_icon = "mdi:crop"

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the select."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_scale_mode"
        self._attr_name = "Photo scale mode"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """Needs the device awake and firmware that reports scaleMode."""
        settings = self.coordinator.data.get("processing_settings", {})
        return super().available and self.coordinator.available and "scaleMode" in settings

    @property
    def current_option(self) -> str | None:
        """Return the current scale mode."""
        settings = self.coordinator.data.get("processing_settings", {})
        return settings.get("scaleMode", "cover")

    async def async_select_option(self, option: str) -> None:
        """Set the scale mode."""
        await self.coordinator.async_set_processing_settings({"scaleMode": option})


class PhotoFrameFitBackgroundSelect(CoordinatorEntity, SelectEntity):
    """Letterbox background color select for PhotoFrame fit mode."""

    _attr_has_entity_name = True
    _attr_options = ["white", "black", "red", "green", "blue", "yellow"]
    _attr_icon = "mdi:format-color-fill"
    _attr_entity_registry_enabled_default = False  # only relevant in fit mode

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the select."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_fit_background_color"
        self._attr_name = "Fit background color"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """Needs the device awake and firmware that reports backgroundColor."""
        settings = self.coordinator.data.get("processing_settings", {})
        return super().available and self.coordinator.available and "backgroundColor" in settings

    @property
    def current_option(self) -> str | None:
        """Return the current background color."""
        settings = self.coordinator.data.get("processing_settings", {})
        return settings.get("backgroundColor", "white")

    async def async_select_option(self, option: str) -> None:
        """Set the letterbox background color."""
        await self.coordinator.async_set_processing_settings({"backgroundColor": option})


class PhotoFrameRotateEnabledSensorSelect(CoordinatorEntity, SelectEntity):
    """Binary sensor that gates auto-rotation on each wake.

    When the frame checks in on wake, HA reports the selected sensor's state;
    if it is off the device skips the rotation (and the e-paper refresh) and
    goes back to sleep until the next scheduled wake — e.g. only rotate when
    someone is home. Pick "None" to always rotate. For richer conditions,
    create a Template binary-sensor helper and select it here. This is HA-side
    logic, stored in the config entry options and never sent to the device.
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:motion-sensor"
    _attr_available = True  # Always editable, even when device is offline

    def __init__(
        self,
        coordinator: PhotoFrameCoordinator,
        entry: ConfigEntry,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the select."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_rotate_enabled_sensor"
        self._attr_name = "Auto rotate enabled sensor"
        self._attr_device_info = coordinator.device_info
        self._hass = hass
        self._entry = entry

    @property
    def options(self) -> list[str]:
        """Return available binary_sensor entities."""
        from homeassistant.helpers import entity_registry as er

        entity_reg = er.async_get(self._hass)
        sensors = {
            entity.entity_id
            for entity in entity_reg.entities.values()
            if entity.domain == "binary_sensor"
        }
        for state in self._hass.states.async_all("binary_sensor"):
            sensors.add(state.entity_id)
        return ["None"] + sorted(sensors)

    @property
    def current_option(self) -> str | None:
        """Return the currently selected gating sensor."""
        return self._entry.options.get("rotate_sensor") or "None"

    async def async_select_option(self, option: str) -> None:
        """Set the gating sensor."""
        new_options = dict(self._entry.options)
        new_options["rotate_sensor"] = option if option != "None" else ""
        self._hass.config_entries.async_update_entry(self._entry, options=new_options)
        self.async_write_ha_state()


class PhotoFrameIpModeSelect(PendingConfigEntityMixin, CoordinatorEntity, SelectEntity):
    """IP configuration mode select for PhotoFrame (#43)."""

    _attr_has_entity_name = True
    _attr_options = ["dhcp", "static"]
    _attr_available = True  # Always editable, even when device is offline
    _config_key = "ip_mode"
    _default_icon = "mdi:ip-network-outline"

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the select."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_ip_mode"
        self._attr_name = "IP configuration"
        self._attr_device_info = coordinator.device_info

    @property
    def current_option(self) -> str | None:
        """Return the current IP mode."""
        config = self.coordinator.data.get("config", {})
        return config.get("ip_mode", "dhcp")

    async def async_select_option(self, option: str) -> None:
        """Set the IP mode.

        The firmware requires valid static_ip/netmask/gateway before accepting
        static mode; it rejects the change otherwise, and the per-key retry in
        the coordinator surfaces that as a discarded pending change.
        """
        await self.coordinator.async_set_config({"ip_mode": option})
