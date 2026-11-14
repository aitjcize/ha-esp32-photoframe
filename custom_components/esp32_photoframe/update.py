"""Update platform for ESP32 PhotoFrame."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import quote

import aiohttp
from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PhotoFrameCoordinator
from .utils import normalize_firmware_version

_LOGGER = logging.getLogger(__name__)

_ACTIVE_OTA_STATES = {"downloading", "installing"}
_OTA_POLL_INTERVAL = 5
_OTA_POLL_ATTEMPTS = 120
_GITHUB_RELEASE_API = "https://api.github.com/repos/aitjcize/esp32-photoframe/releases/tags/{tag}"
_GITHUB_RELEASE_URL = "https://github.com/aitjcize/esp32-photoframe/releases/tag/{tag}"
_GITHUB_HEADERS = {"Accept": "application/vnd.github+json"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the update platform."""
    coordinator: PhotoFrameCoordinator = hass.data[DOMAIN][entry.entry_id]

    # The update entity replaces the old "Update firmware" button one for one,
    # so its registry entry goes. The Current version / Latest version / OTA
    # state sensors stay for now (deprecated, disabled by default on new
    # installs): people have them on dashboards and in automations.
    entity_registry = er.async_get(hass)
    button_entity_id = entity_registry.async_get_entity_id(
        "button", DOMAIN, f"{entry.entry_id}_ota_update"
    )
    if button_entity_id is not None:
        entity_registry.async_remove(button_entity_id)

    async_add_entities([PhotoFrameFirmwareUpdate(coordinator, entry)])


class PhotoFrameFirmwareUpdate(CoordinatorEntity, UpdateEntity):
    """Firmware update entity for a PhotoFrame."""

    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_has_entity_name = True
    _attr_name = "Firmware"
    _attr_supported_features = (
        UpdateEntityFeature.INSTALL
        | UpdateEntityFeature.PROGRESS
        | UpdateEntityFeature.RELEASE_NOTES
    )

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the update entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_firmware_update"
        self._attr_device_info = coordinator.device_info
        self._install_task: asyncio.Task[None] | None = None
        self._release_notes_version: str | None = None
        self._release_notes: str | None = None

    @property
    def available(self) -> bool:
        """Keep cached firmware information visible while the frame sleeps."""
        return bool(self.installed_version or self.latest_version)

    @property
    def installed_version(self) -> str | None:
        """Return the installed firmware version."""
        return self.coordinator.data.get("ota", {}).get("current_version") or None

    @property
    def latest_version(self) -> str | None:
        """Return the latest firmware version."""
        return self.coordinator.data.get("ota", {}).get("latest_version") or None

    @property
    def release_url(self) -> str | None:
        """Return the latest firmware release page URL."""
        if not self.latest_version:
            return None
        return _GITHUB_RELEASE_URL.format(tag=quote(self.latest_version, safe=""))

    async def async_release_notes(self) -> str | None:
        """Fetch the latest firmware release notes from GitHub."""
        version = self.latest_version
        if not version:
            return None
        if self._release_notes_version == version:
            return self._release_notes

        try:
            async with self.coordinator.session.get(
                _GITHUB_RELEASE_API.format(tag=quote(version, safe="")),
                headers=_GITHUB_HEADERS,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status != 200:
                    _LOGGER.warning(
                        "Failed to fetch release notes for %s: HTTP %s",
                        version,
                        response.status,
                    )
                    return None
                payload = await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.warning("Failed to fetch release notes for %s: %s", version, err)
            return None

        self._release_notes_version = version
        self._release_notes = payload.get("body") or None
        return self._release_notes

    @property
    def in_progress(self) -> bool:
        """Return whether an OTA install is under way."""
        ota_data = self.coordinator.data.get("ota", {})
        if ota_data.get("state") in _ACTIVE_OTA_STATES:
            return True
        return self._install_task is not None and not self._install_task.done()

    @property
    def update_percentage(self) -> int | None:
        """Return the install progress the frame reports, if it is installing."""
        ota_data = self.coordinator.data.get("ota", {})
        if ota_data.get("state") not in _ACTIVE_OTA_STATES:
            return None
        progress = int(ota_data.get("progress_percent") or 0)
        return progress if progress > 0 else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose device OTA diagnostics on the update entity."""
        ota_data = self.coordinator.data.get("ota", {})
        return {
            "ota_state": ota_data.get("state", "idle"),
            "ota_error": ota_data.get("error_message") or None,
        }

    async def async_install(self, version: str | None, backup: bool, **kwargs: Any) -> None:
        """Trigger the device's OTA firmware update."""
        ota_data = self.coordinator.data.get("ota", {})
        if ota_data.get("state") in _ACTIVE_OTA_STATES:
            raise HomeAssistantError("Firmware update is already in progress")

        # /api/ota/check is synchronous on the frame (up to 30 s) and answers
        # with the result, leaving the device in the update_available state
        # that /api/ota/update requires.
        check = await self._async_post_ota("check", timeout=40)
        if not check.get("update_available"):
            await self.coordinator.async_refresh_ota_status()
            raise HomeAssistantError("The frame reports no firmware update available")

        await self._async_post_ota("update", timeout=10)

        self._install_task = self.hass.async_create_task(
            self._async_track_install(),
            name=f"esp32_photoframe_ota_{self._attr_unique_id}",
        )
        self.async_write_ha_state()

    async def _async_post_ota(self, action: str, timeout: int) -> dict[str, Any]:
        """Call an OTA action and validate its JSON response."""
        try:
            async with self.coordinator.session.post(
                f"{self.coordinator.host}/api/ota/{action}",
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as response:
                if response.status != 200:
                    raise HomeAssistantError(f"OTA {action} failed: HTTP {response.status}")
                try:
                    payload = await response.json(content_type=None)
                except ValueError as err:
                    raise HomeAssistantError(
                        f"OTA {action} failed: unexpected reply from the frame"
                    ) from err
                if payload.get("status") != "success":
                    raise HomeAssistantError(
                        payload.get("message", f"Device rejected OTA {action}")
                    )
        except aiohttp.ClientError as err:
            raise HomeAssistantError(f"OTA {action} failed: {err}") from err
        return payload

    async def _async_track_install(self) -> None:
        """Track OTA progress until the device reports a terminal state."""
        try:
            for _ in range(_OTA_POLL_ATTEMPTS):
                await asyncio.sleep(_OTA_POLL_INTERVAL)
                ota_data = await self.coordinator.async_refresh_ota_status()
                if not ota_data:
                    continue

                state = ota_data.get("state")
                if state == "error":
                    _LOGGER.error(
                        "Firmware update failed: %s",
                        ota_data.get("error_message") or "unknown device error",
                    )
                    return
                if state == "success":
                    # Installed; the frame reboots next and reports the new
                    # version when it checks in.
                    return
                current_version = normalize_firmware_version(ota_data.get("current_version"))
                latest_version = normalize_firmware_version(ota_data.get("latest_version"))
                if state == "idle" and current_version and current_version == latest_version:
                    return

            _LOGGER.warning("Timed out waiting for firmware update status")
        finally:
            self._install_task = None
            self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Cancel OTA tracking when the entity is removed."""
        if self._install_task is not None:
            self._install_task.cancel()
        await super().async_will_remove_from_hass()
