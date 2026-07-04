"""DataUpdateCoordinator for ESP32 PhotoFrame."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_BATTERY,
    API_CONFIG,
    API_DISPLAY_IMAGE,
    API_OTA_STATUS,
    API_SENSOR,
    API_SYSTEM_INFO,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class PhotoFrameCoordinator(DataUpdateCoordinator):
    """Class to manage fetching PhotoFrame data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        self.host = entry.data[CONF_HOST]
        self.session = async_get_clientsession(hass)
        self.entry = entry
        self.hass = hass

        # Store last known battery data to preserve when device is asleep
        self._last_battery_data = {}

        # Store last known OTA data to preserve when device is asleep
        self._last_ota_data = {}

        # Store last known sensor data to preserve when device is asleep
        self._last_sensor_data = {}

        # Store cached image uploaded by device (for deep sleep support)
        self._cached_image: bytes | None = None

        # Track if last image fetch was successful (to prevent timestamp updates on failures)
        self._image_fetch_successful: bool = False

        # Track device online/offline state (set by explicit notifications)
        self._device_online: bool = True

        # Track last update time for availability
        self._last_update_time: datetime | None = None
        self._availability_timeout = timedelta(minutes=2)  # Device offline after 2 min
        self._availability_check_interval = timedelta(minutes=1)  # Check periodically when offline
        self._availability_check_task: asyncio.Task | None = None

        # Cache last known config data from device
        self._last_config_data: dict[str, Any] = {}

        # Pending config changes to push to device when it next wakes up
        pending = entry.data.get("pending_config_changes", {})
        self._pending_config_changes: dict[str, Any] = (
            dict(pending) if isinstance(pending, dict) else {}
        )

        # Device message from the most recent semantic (HTTP 400) rejection,
        # consumed by async_set_config to surface the error to the user
        self._last_rejection: str | None = None

        # System info
        self.system_info: dict[str, Any] = {}

        # Centralized device info for all entities
        device_name = entry.data.get("device_name", "ESP32-S3-PhotoPainter")
        device_id = entry.data.get("device_id")
        self.device_info = {
            "identifiers": {(DOMAIN, device_id if device_id else entry.entry_id)},
            "name": device_name,
            "manufacturer": "Waveshare",
            "model": "ESP32-S3-PhotoPainter",
        }

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            # Poll every 10 minutes for battery and OTA updates
            # Device will be marked offline after 2 minutes of no response
            update_interval=timedelta(minutes=10),
        )

        # Start availability monitoring task (background so it doesn't block HA bootstrap)
        self._availability_check_task = hass.async_create_background_task(
            self._availability_check_loop(),
            name=f"esp32_photoframe_{self.host}_availability_check",
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        # Called periodically and when device sends notification
        # Notifications provide immediate updates, polling provides regular battery/OTA checks
        try:
            # Fetch battery first. The device is only awake for a brief window
            # (~10s) after waking from deep sleep, so we grab the highest-value
            # reading before anything slower. _fetch_battery never raises (it
            # returns {} on failure), so unlike the config fetch below it can't
            # short-circuit the rest of the update. This is the key fix for
            # battery levels going stale: previously config was fetched first
            # and, when it raised, battery was never attempted at all.
            _LOGGER.debug("Fetching battery data from %s", self.host)
            battery_data = await self._fetch_battery()

            # If we got battery data, update our cache and timestamp
            if battery_data:
                _LOGGER.debug(
                    "Battery data fetched successfully: %s%%",
                    battery_data.get("battery_level"),
                )
                self._last_battery_data = battery_data
                self._last_update_time = datetime.now()
            # Otherwise, use the last known battery data
            else:
                _LOGGER.debug("Using cached battery data")
                battery_data = self._last_battery_data

            # Fetch sensor data next (also cheap and time-sensitive)
            _LOGGER.debug("Fetching sensor data from %s", self.host)
            sensor_data = await self._fetch_sensor()

            # If we got sensor data, update our cache
            if sensor_data:
                _LOGGER.debug(
                    "Sensor data fetched successfully: %.1f°C, %.1f%%",
                    sensor_data.get("temperature", 0),
                    sensor_data.get("humidity", 0),
                )
                self._last_sensor_data = sensor_data
            # Otherwise, use the last known sensor data
            else:
                _LOGGER.debug("Using cached sensor data")
                sensor_data = self._last_sensor_data

            # Try to fetch config data (may fail if device is asleep)
            _LOGGER.debug("Fetching config data from %s", self.host)
            config_data = await self._fetch_config()
            _LOGGER.debug("Config data fetched: %s", bool(config_data))
            if config_data:
                self._last_config_data = config_data
                # Device is online — push any pending config changes now
                if self._pending_config_changes:
                    _LOGGER.info(
                        "Device online with %d pending config change(s), pushing",
                        len(self._pending_config_changes),
                    )
                    self.hass.async_create_task(self.async_push_pending_config())

            # Self-healing: Check if device_id matches ConfigEntry
            # This fixes issues where device_id was missing or incorrect during initial setup
            if config_data and "device_id" in config_data:
                remote_device_id = config_data["device_id"]
                current_device_id = self.entry.data.get("device_id")

                if remote_device_id and remote_device_id != current_device_id:
                    _LOGGER.info(
                        "Updating ConfigEntry device_id from '%s' to '%s'",
                        current_device_id,
                        remote_device_id,
                    )
                    # Update the config entry with the correct device_id
                    new_data = {**self.entry.data}
                    new_data["device_id"] = remote_device_id
                    self.hass.config_entries.async_update_entry(self.entry, data=new_data)

            # Try to fetch OTA data
            _LOGGER.debug("Fetching OTA status from %s", self.host)
            ota_data = await self._fetch_ota_status()

            # If we got OTA data, update our cache
            if ota_data:
                _LOGGER.debug("OTA data fetched successfully: %s", ota_data.get("current_version"))
                self._last_ota_data = ota_data
            # Otherwise, use the last known OTA data
            else:
                _LOGGER.debug("Using cached OTA data")
                ota_data = self._last_ota_data

            # Try to fetch system info if not already fetched
            if not self.system_info:
                _LOGGER.debug("Fetching system info from %s", self.host)
                system_info = await self._fetch_system_info()
                if system_info:
                    self.system_info = system_info
                    self._apply_board_identity(system_info)

            # Try to fetch current image (may fail if device is asleep)
            _LOGGER.debug("Fetching current image from %s", self.host)
            try:
                await self.fetch_current_image()
            except (aiohttp.ClientError, UpdateFailed):
                # Keep existing cached image if fetch fails
                _LOGGER.debug("Failed to fetch current image, keeping cached version")

            return {
                "config": self._get_effective_config(),
                "battery": battery_data,
                "ota": ota_data,
                "sensor": sensor_data,
            }
        except (
            aiohttp.ClientError,
            asyncio.TimeoutError,
            OSError,
            UpdateFailed,
        ) as err:
            # Device is likely offline/asleep - use cached data instead of failing
            if self._last_battery_data or self._last_ota_data or self._last_sensor_data:
                _LOGGER.debug("Device offline/asleep, using cached values: %s", err)
                return {
                    "config": self._get_effective_config(),
                    "battery": self._last_battery_data,
                    "ota": self._last_ota_data,
                    "sensor": self._last_sensor_data,
                }
            # Device is offline during setup (e.g., HA restart while device asleep)
            # Return empty data to allow integration to load - it will update when device wakes
            _LOGGER.warning(
                "Device offline during setup (likely in deep sleep), integration will update when device wakes: %s",
                err,
            )
            return {
                "config": self._get_effective_config(),
                "battery": {},
                "ota": {},
                "sensor": {},
            }

    async def _fetch_config(self) -> dict[str, Any]:
        """Fetch config from photoframe."""
        try:
            async with self.session.get(
                f"{self.host}{API_CONFIG}",
                # Keep inside the device's ~10s post-wake window so a slow config
                # fetch can't block the update; battery/sensor are fetched first.
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status != 200:
                    raise UpdateFailed(f"HTTP {response.status}")
                return await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as err:
            raise UpdateFailed(f"Failed to fetch config: {err}")

    async def _fetch_battery(self) -> dict[str, Any]:
        """Fetch battery data from photoframe."""
        try:
            async with self.session.get(
                f"{self.host}{API_BATTERY}",
                # Short timeout: battery is fetched first inside the ~10s wake
                # window and the endpoint responds quickly when the device is up.
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status != 200:
                    _LOGGER.debug("Battery endpoint returned HTTP %s", response.status)
                    return {}
                return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.debug("Failed to fetch battery data: %s", err)
            return {}

    async def _fetch_ota_status(self) -> dict[str, Any]:
        """Fetch OTA status data from photoframe."""
        try:
            async with self.session.get(
                f"{self.host}{API_OTA_STATUS}",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status != 200:
                    _LOGGER.debug("OTA status endpoint returned HTTP %s", response.status)
                    return {}
                data = await response.json()
                # Extract the fields we need from the OTA status response
                return {
                    "current_version": data.get("current_version", ""),
                    "latest_version": data.get("latest_version", ""),
                    "state": data.get("state", "idle"),
                }
        except aiohttp.ClientError as err:
            _LOGGER.debug("Failed to fetch OTA status: %s", err)
            return {}

    async def _fetch_sensor(self) -> dict[str, Any]:
        """Fetch sensor data (temperature/humidity) from photoframe."""
        try:
            async with self.session.get(
                f"{self.host}{API_SENSOR}",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status != 200:
                    _LOGGER.debug("Sensor endpoint returned HTTP %s", response.status)
                    return {}
                data = await response.json()
                # Only return data if sensor is available and read was successful
                if data.get("status") == "ok":
                    return {
                        "temperature": data.get("temperature"),
                        "humidity": data.get("humidity"),
                        "available": True,
                    }
                else:
                    _LOGGER.debug("Sensor not available or read error: %s", data.get("status"))
                    return {"available": False}
        except aiohttp.ClientError as err:
            _LOGGER.debug("Failed to fetch sensor data: %s", err)
            return {}

    async def _fetch_system_info(self) -> dict[str, Any]:
        """Fetch system info from photoframe."""
        try:
            async with self.session.get(
                f"{self.host}{API_SYSTEM_INFO}",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status != 200:
                    _LOGGER.debug("System info endpoint returned HTTP %s", response.status)
                    return {}
                return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.debug("Failed to fetch system info: %s", err)
            return {}

    def _apply_board_identity(self, system_info: dict[str, Any]) -> None:
        """Surface the real board as the HA device manufacturer/model.

        device_info is created before system info is known, so it defaults to the
        Waveshare PhotoPainter. Once the device reports its board_name (e.g.
        seeedstudio_reterminal_e1003 for a grayscale GC16 panel), update the
        registry so make/model are correct rather than always "Waveshare".
        """
        board = system_info.get("board_name") or ""
        if not board:
            return
        if board.startswith("seeedstudio"):
            manufacturer = "Seeed Studio"
        elif board.startswith("waveshare"):
            manufacturer = "Waveshare"
        else:
            manufacturer = "ESP32 PhotoFrame"
        if (
            self.device_info.get("manufacturer") == manufacturer
            and self.device_info.get("model") == board
        ):
            return
        self.device_info["manufacturer"] = manufacturer
        self.device_info["model"] = board
        registry = dr.async_get(self.hass)
        device = registry.async_get_device(identifiers=self.device_info["identifiers"])
        if device:
            registry.async_update_device(device.id, manufacturer=manufacturer, model=board)

    async def fetch_current_image(self) -> None:
        """Fetch and cache the current image from the device."""
        # Reset success flag before attempting fetch
        self._image_fetch_successful = False

        try:
            from .const import API_CURRENT_IMAGE

            async with self.session.get(
                f"{self.host}{API_CURRENT_IMAGE}",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    self._cached_image = await response.read()
                    self._image_fetch_successful = True  # Mark as successful
                    _LOGGER.debug(
                        "Fetched and cached current image (%d bytes)",
                        len(self._cached_image),
                    )
                elif response.status == 404:
                    _LOGGER.debug("No image currently displayed on device")
                    # Don't clear cache - keep showing last known image
                else:
                    _LOGGER.debug("Failed to fetch current image: HTTP %s", response.status)
                    # Don't clear cache - keep showing last known image
        except aiohttp.ClientError as err:
            _LOGGER.debug("Failed to fetch current image: %s", err)
            # Don't clear cache - preserve last known image for offline support

    def _get_effective_config(self) -> dict[str, Any]:
        """Return effective config: last known device config merged with pending changes."""
        return {**self._last_config_data, **self._pending_config_changes}

    def _save_pending_config(self) -> None:
        """Persist pending config changes to config entry data."""
        new_data = {
            **self.entry.data,
            "pending_config_changes": dict(self._pending_config_changes),
        }
        self.hass.config_entries.async_update_entry(self.entry, data=new_data)

    def is_key_pending(self, key: str) -> bool:
        """Return True if the given config key has an unpushed pending change."""
        return key in self._pending_config_changes

    @property
    def has_config_data(self) -> bool:
        """Return True if we have any knowledge of the device's config.

        False means we've never successfully talked to the device in this
        HA session and have no pending edits either — in that case config
        controls should be disabled because we have no current value to show.
        """
        return bool(self._last_config_data or self._pending_config_changes)

    @staticmethod
    async def _response_message(response: aiohttp.ClientResponse) -> str:
        """Extract the device's error message from a config response, if any."""
        try:
            body = await response.json(content_type=None)
            if isinstance(body, dict) and isinstance(body.get("message"), str):
                return body["message"]
        except (aiohttp.ClientError, ValueError):
            pass
        return ""

    async def _push_config_keys_individually(self, config: dict[str, Any]) -> None:
        """Retry a rejected batch one key at a time, discarding rejected keys.

        The device validates config semantically and rejects the whole PATCH
        on the first invalid value, so a single bad entry (e.g. a typoed cron
        rule) would otherwise wedge every other queued change in the pending
        queue forever. Keys the device accepts are applied and cleared; keys
        it rejects with HTTP 400 are dropped with an error so the queue heals.
        """
        for key, value in config.items():
            if key not in self._pending_config_changes:
                continue
            try:
                async with self.session.patch(
                    f"{self.host}{API_CONFIG}",
                    json={key: value},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        self._last_config_data[key] = value
                        self._pending_config_changes.pop(key, None)
                    elif response.status == 400:
                        msg = await self._response_message(response)
                        self._last_rejection = msg or f"invalid value for {key}"
                        self._pending_config_changes.pop(key, None)
                        _LOGGER.error(
                            "Device rejected config %r (%s); discarding the change",
                            key,
                            self._last_rejection,
                        )
                    else:
                        _LOGGER.warning(
                            "Failed to push config %r: HTTP %s; will retry later",
                            key,
                            response.status,
                        )
            except aiohttp.ClientError as err:
                _LOGGER.debug("Device went away during per-key config push: %s", err)
                break
        self._save_pending_config()
        self.async_update_listeners()
        # Re-fetch so any optimistic value from a rejected key is replaced by
        # the device's actual config.
        self.hass.async_create_task(self.async_request_refresh())

    async def async_push_pending_config(self) -> bool:
        """Push all pending config changes to device via PATCH /api/config."""
        if not self._pending_config_changes:
            return True

        config_to_push = dict(self._pending_config_changes)
        _LOGGER.info("Pushing %d pending config change(s) to device", len(config_to_push))
        try:
            async with self.session.patch(
                f"{self.host}{API_CONFIG}",
                json=config_to_push,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 400:
                    # Semantic rejection, not an offline device: some value in
                    # the batch is invalid. Retry per key so the valid changes
                    # still apply and only the bad one is dropped.
                    msg = await self._response_message(response)
                    _LOGGER.warning(
                        "Device rejected pending config (%s); retrying keys individually",
                        msg or "no message",
                    )
                    await self._push_config_keys_individually(config_to_push)
                    return False
                if response.status != 200:
                    _LOGGER.warning("Failed to push pending config: HTTP %s", response.status)
                    return False
                # Merge pushed values into last-known config so effective config stays correct
                self._last_config_data.update(config_to_push)
                self._pending_config_changes.clear()
                self._save_pending_config()
                # Notify entities so they clear the pending indicator
                self.async_update_listeners()
                _LOGGER.info("Pending config changes pushed successfully")
                # Re-fetch full config from device: the user may have edited
                # settings from the device web UI while HA was offline, so we
                # want those to show up in HA too.
                self.hass.async_create_task(self.async_request_refresh())
                return True
        except aiohttp.ClientError as err:
            _LOGGER.debug("Failed to push pending config to device: %s", err)
            return False

    async def async_set_config(self, config: dict[str, Any]) -> bool:
        """Cache a config change and push to device if it is currently available.

        Changes are always persisted so they are delivered on the next device
        wake-up even if the device is currently in deep sleep.
        """
        # Optimistic update: reflect the change immediately in both caches
        self._pending_config_changes.update(config)
        self._last_config_data.update(config)

        # Persist pending changes so they survive HA restarts
        self._save_pending_config()

        # Update coordinator data so all entities see the new values right away
        if self.data is not None:
            self.async_set_updated_data({**self.data, "config": self._get_effective_config()})

        # Attempt an immediate push if device is currently reachable
        if self.available:
            self._last_rejection = None
            await self.async_push_pending_config()
            if self._last_rejection:
                msg = self._last_rejection
                self._last_rejection = None
                raise HomeAssistantError(f"PhotoFrame rejected the change: {msg}")

        return True

    async def async_display_image(self, image_data: bytes) -> bool:
        """Send image to photoframe for display."""
        try:
            async with self.session.post(
                f"{self.host}{API_DISPLAY_IMAGE}",
                data=image_data,
                headers={"Content-Type": "image/jpeg"},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to display image: HTTP %s", response.status)
                    return False
                return True
        except aiohttp.ClientError as err:
            _LOGGER.error("Failed to display image: %s", err)
            return False

    @property
    def available(self) -> bool:
        """Return if device is available based on explicit online/offline state and timeout.

        Device is considered available if:
        1. Explicitly marked as online (_device_online = True), AND
        2. Either has recent successful update OR within timeout period
        """
        # If device explicitly notified offline, it's unavailable
        if not self._device_online:
            return False

        # If no update time recorded yet, unavailable
        if self._last_update_time is None:
            return False

        # Check if within timeout period
        time_since_update = datetime.now() - self._last_update_time
        return time_since_update < self._availability_timeout

    async def _availability_check_loop(self) -> None:
        """Periodically check device availability when offline."""
        while True:
            try:
                # Wait for the check interval
                await asyncio.sleep(self._availability_check_interval.total_seconds())

                # Only check if device is currently unavailable
                if not self.available:
                    _LOGGER.debug("Device unavailable, checking if it's back online")
                    try:
                        # Try to refresh data to check if device is back
                        await self.async_request_refresh()
                        if self.available:
                            _LOGGER.info("Device is back online")
                    except Exception as err:
                        _LOGGER.debug("Availability check failed: %s", err)
            except asyncio.CancelledError:
                _LOGGER.debug("Availability check task cancelled")
                break
            except Exception as err:
                _LOGGER.error("Error in availability check loop: %s", err)
                # Wait before retrying to avoid tight loop on persistent errors
                await asyncio.sleep(60)

    @property
    def has_storage(self) -> bool:
        """Return if device has storage (SD card or internal flash)."""
        return self.system_info.get("sdcard_inserted", True) or self.system_info.get(
            "has_flash_storage", False
        )  # Default sdcard_inserted to True for backward compatibility


class PendingConfigEntityMixin:
    """Mixin for entities backed by a config key that may have pending changes.

    Subclasses set `_config_key` (the key in the device config dict they manage)
    and `_default_icon` (the normal icon). When that key has an unpushed pending
    change, the entity's icon switches to a progress-clock icon and
    `extra_state_attributes` exposes `pending_change: True`, giving users visual
    feedback that the setting will be applied on next device wake-up.
    """

    _config_key: str | None = None
    _default_icon: str | None = None

    @property
    def available(self) -> bool:
        """Editable whenever we have any known config state.

        Bypasses `CoordinatorEntity.available`'s `last_update_success` check
        so a transient polling failure (e.g. device dozing off after an
        auto-rotate cycle) doesn't lock the user out. But if we have never
        successfully fetched config and have no pending edits either — for
        example after an HA restart while the device is offline — we keep
        the control disabled because there is no current value to edit.
        """
        coordinator: PhotoFrameCoordinator | None = getattr(self, "coordinator", None)
        return coordinator is not None and coordinator.has_config_data

    @property
    def icon(self) -> str | None:
        coordinator: PhotoFrameCoordinator | None = getattr(self, "coordinator", None)
        if (
            coordinator is not None
            and self._config_key
            and coordinator.is_key_pending(self._config_key)
        ):
            return "mdi:progress-clock"
        return self._default_icon

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        coordinator: PhotoFrameCoordinator | None = getattr(self, "coordinator", None)
        if (
            coordinator is not None
            and self._config_key
            and coordinator.is_key_pending(self._config_key)
        ):
            return {"pending_change": True}
        return None
