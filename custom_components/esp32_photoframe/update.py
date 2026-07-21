"""Update platform for ESP32 PhotoFrame."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

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
_OTA_CHECK_ATTEMPTS = 40


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the update platform."""
    coordinator: PhotoFrameCoordinator = hass.data[DOMAIN][entry.entry_id]

    entity_registry = er.async_get(hass)
    for entity_domain, unique_id_suffix in (
        ("sensor", "current_version"),
        ("sensor", "latest_version"),
        ("sensor", "ota_state"),
        ("button", "ota_update"),
    ):
        entity_id = entity_registry.async_get_entity_id(
            entity_domain,
            DOMAIN,
            f"{entry.entry_id}_{unique_id_suffix}",
        )
        if entity_id is not None:
            entity_registry.async_remove(entity_id)

    async_add_entities([PhotoFrameFirmwareUpdate(coordinator, entry)])


class PhotoFrameFirmwareUpdate(CoordinatorEntity, UpdateEntity):
    """Firmware update entity for a PhotoFrame."""

    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_has_entity_name = True
    _attr_name = "Firmware"
    _attr_supported_features = UpdateEntityFeature.INSTALL | UpdateEntityFeature.PROGRESS

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the update entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_firmware_update"
        self._attr_device_info = coordinator.device_info
        self._install_task: asyncio.Task[None] | None = None

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
    def in_progress(self) -> bool | int:
        """Return OTA installation progress."""
        ota_data = self.coordinator.data.get("ota", {})
        if ota_data.get("state") in _ACTIVE_OTA_STATES:
            progress = int(ota_data.get("progress_percent", 0))
            return progress if progress > 0 else True
        return self._install_task is not None and not self._install_task.done()

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

        await self._async_post_ota("check", timeout=40)
        await self._async_wait_for_update_check()

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
                payload = await response.json(content_type=None)
                if response.status != 200:
                    raise HomeAssistantError(f"OTA {action} failed: HTTP {response.status}")
                if payload.get("status") != "success":
                    raise HomeAssistantError(
                        payload.get("message", f"Device rejected OTA {action}")
                    )
        except aiohttp.ClientError as err:
            raise HomeAssistantError(f"OTA {action} failed: {err}") from err
        return payload

    async def _async_wait_for_update_check(self) -> None:
        """Wait for the device's asynchronous OTA check to finish."""
        await asyncio.sleep(1)
        for _ in range(_OTA_CHECK_ATTEMPTS):
            ota_data = await self.coordinator.async_refresh_ota_status()
            if not ota_data:
                await asyncio.sleep(1)
                continue

            state = ota_data.get("state")
            if state == "update_available":
                return
            if state == "error":
                raise HomeAssistantError(
                    ota_data.get("error_message") or "Firmware update check failed"
                )
            if state == "idle":
                raise HomeAssistantError("No firmware update is available")

            await asyncio.sleep(1)

        raise HomeAssistantError("Timed out waiting for firmware update check")

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
