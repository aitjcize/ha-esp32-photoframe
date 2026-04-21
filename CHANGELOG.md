# Changelog

## v2.7.1

### Changed
- Removed the gear/options flow entirely. All three fields it used to expose were already first-class HA entities, which was the actual source of truth — having them in two places silently diverged when edited:
  - `ha_url` → edit via the Home Assistant URL text entity (falls back to HA's configured internal/external URL via `get_url()` when empty)
  - `use_ha_images` → edit via the Use HA Images switch entity
  - `media_entity_id` → edit via the Media Entity select entity

## v2.6.8

### Added
- **Offline config editing.** Device settings (rotation mode, orientation,
  auto-rotate, deep sleep, sleep schedule, image URL, HA URL, rotation
  interval, timezone, etc.) can now be edited while the photoframe is in
  deep sleep. Changes are cached in the config entry and delivered via
  `PATCH /api/config` the next time the device notifies Home Assistant
  that it's online.
- **Pending-change indicator.** Entities with a queued but undelivered
  change display an `mdi:progress-clock` icon and expose
  `pending_change: true` in their attributes. The indicator clears
  automatically once the change is pushed.
- **Post-push refresh.** After a successful push, HA refetches the
  device's full config so edits made via the device web UI are
  reflected in HA entities.

### Changed
- Config controls stay available through transient polling failures
  (e.g. a poll landing during a post-auto-rotate sleep cycle) — they no
  longer flip to unavailable just because `last_update_success` toggled.

### Disabled states
- Config controls are still disabled when there is genuinely no state to
  show — e.g. after an HA restart while the device is offline and with
  no pending edits queued.

## v2.6.0 (2026-03-19)

### Fixed
- Availability check loop no longer blocks Home Assistant bootstrap; it
  now runs as a background task so initial setup completes promptly even
  when the device is asleep.

## v2.5.9 (2026-03-08)

### Added
- Support for devices using internal flash storage in addition to SD
  cards.

### Fixed
- Notification endpoint (`/api/esp32_photoframe/notify`) is now registered
  once per HA session and persists across integration reloads, so the
  device can always reach HA to announce state changes.

## v2.5.4 (2026-02-17)

### Fixed
- Auto-rotate switch is now available on devices that have no SD card.

## v2.4.1 (2026-02-06)

### Added
- Support for devices without an SD card (URL-only rotation).
- Coordinators are matched to incoming device notifications by device ID
  instead of host, so changing the host address no longer breaks the
  link between device and HA integration.

## v2.0.2 (2026-01-21)

Initial public release.

### Added
- Battery level & voltage sensors, with caching so last-known values
  remain visible while the device is in deep sleep.
- OTA firmware update support and status reporting.
- Temperature / humidity sensor support, with graceful handling when
  the sensor is absent or unreadable.
- Sleep schedule (start / end time entities + schedule switch).
- Timezone configuration.
- Current image entity that shows the image currently displayed on the
  photoframe, cached for offline viewing.
- Image serving endpoint (`/api/esp32_photoframe/image`) that forwards
  images from any HA camera or image entity to the photoframe.
- Device-initiated notify endpoint for low-latency state updates; HA
  polls only as a fallback, reducing power use vs. constant polling.
- Automatic re-enablement of controls when the device comes back online.
- Device name is populated from the device's reported name rather than a
  generic default.

### Changed
- Images are only re-rendered when they have actually changed, avoiding
  unnecessary e-paper refreshes.
