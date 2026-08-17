# Changelog

## v2.10.0

### Added

- **Photo scale mode and fit background entities.** A *Photo scale mode*
  select (cover/fit) and a *Fit background color* select (white/black)
  control how the frame lays out photos, backed by the device's synced
  processing settings — a change made in Home Assistant reaches the
  device, the server, and the web apps. Requires firmware v2.16.0; on
  older firmware the entities show as unavailable.
- **Full processing-settings parity.** Dither algorithm, tone mapping and
  color matching selects; exposure, saturation, contrast and the four
  s-curve numbers; and a compress-dynamic-range switch. All are
  registry-disabled by default (image tuning is a set-once affair —
  enable the ones you automate) and unavailable while the frame sleeps.
  Writes fetch the frame's current settings and merge the change under a
  lock, so concurrent automations and device-side edits can't overwrite
  each other.


## v2.9.3

### Added

- **Advanced network entities.** New controls for the network configuration
  added in firmware v2.15.0 (#43):
  - **IP configuration** select (Automatic/DHCP or Static IP).
  - **Static IP address**, **Static netmask** and **Static gateway** text
    fields. These are grayed out (unavailable) while the mode is DHCP and
    enable immediately when the select is flipped to *static*, so the whole
    set can be filled in and pushed to the device as one batch.
  - **DNS server** override text field, editable in both IP modes (empty =
    automatic).

  Like the scheduling entities, these appear only on firmware that supports
  them — devices on older firmware are unaffected.
- **NTP server** text entity (supported by all firmware versions).

## v2.9.2

### Changed

- **Firmware-aware scheduling entities.** Scheduling controls now appear only on
  the firmware that supports them, instead of lingering as permanently
  *unavailable*:
  - The **Rotation schedule** (cron) text entity shows only on cron firmware.
  - The legacy **Sleep schedule** switch and **Sleep schedule start**/**end**
    times show only on pre-cron firmware.

  The set is chosen from what the device reports, so an OTA between firmware
  generations swaps the entities automatically — the stale ones are removed once
  the device checks in on its new firmware (no manual cleanup needed).

- The device's last-known config is now cached to the config entry, so entities
  and their editable values resolve immediately after a Home Assistant restart
  instead of waiting for a deep-sleeping frame to next check in.

## v2.9.1

### Changed

- Read the device's `device_id` from `/api/system-info` (the canonical identity
  endpoint) instead of `/api/config`. No user-facing change — this lets upcoming
  firmware drop the duplicate `device_id` from `/api/config`. Update this
  integration before flashing that firmware.

## v2.9.0

### Added
- **Rotation gate** — a new **Auto rotate enabled sensor** select lets you skip
  image rotations based on a binary sensor. When the frame wakes it checks in
  with HA; if the chosen sensor is off, the device goes back to sleep without
  refreshing (and without the e-paper flash), saving battery — e.g. only rotate
  when someone is home. Pick "None" to always rotate. For richer conditions
  (presence *and* daytime, etc.), create a Template binary-sensor helper
  (Settings → Devices & Services → Helpers) and select it here. The cron wake
  schedule is unchanged; this only decides whether each wake actually rotates.
  Requires firmware with rotation-gate support.

## v2.8.0

### Changed
- **Rotation schedule is now cron-based.** The firmware replaced the single
  rotation interval with a list of simplified 3-field cron rules
  (`minute hour day-of-week`). The **Rotation interval** number entity is
  therefore replaced by a **Rotation schedule** text entity
  (`text.esp32_photoframe_rotation_schedule`) that reads and writes
  `rotate_cron`. Enter one or more rules separated by `;`, e.g. `0 */12 *` or
  `0 9 1-5; 0 18 0,6`. The friendly schedule builder lives in the device web
  UI, the mobile app, and the image server.
  - **Breaking:** automations referencing
    `number.esp32_photoframe_rotation_interval` must be updated to the new
    text entity; the old registry entry is removed automatically on upgrade.
  - The schedule entity requires firmware with cron support (it shows as
    unavailable on older firmware, which doesn't understand `rotate_cron`).
- **The Sleep schedule (quiet hours) is now a legacy feature.** Cron firmware
  bounds the active hours in the schedule rules (e.g. `0 7-23/2 *`, or two
  rules for overnight coverage) instead of a separate quiet-hours window, so
  the **Sleep schedule** switch and the **Sleep schedule start/end** time
  entities now show as **unavailable** on cron firmware. They remain usable on
  older (pre-cron) firmware.

### Fixed
- A config value rejected by the device (e.g. an invalid cron rule) no longer
  wedges the pending-change queue: valid queued changes are still applied,
  the rejected value is discarded, and the device's error message is shown in
  the UI instead of the bad value appearing accepted.

## v2.7.3

### Added
- Brand icon for the integration. Home Assistant 2026.3.0+ reads it directly from `custom_components/esp32_photoframe/brand/`, so the device list and config flow now show the photoframe icon instead of the generic placeholder. Same artwork as the firmware webapp and the HA add-on, so the whole ecosystem shares one brand mark.

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
