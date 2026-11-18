# Changelog

## v2.13.0

### Fixed

- **Security: the served image was public.** With **Use HA images**, the
  frame fetches its picture from `/api/esp32_photoframe/image`, which needs
  no Home Assistant login because the frame cannot log in. Anyone who could
  reach Home Assistant, including over the internet through a reverse proxy
  or Home Assistant Cloud, could fetch the configured camera or image (#12).
  Each frame now fetches `/api/esp32_photoframe/image/<token>`, with a random
  token kept in its config entry, and the view serves nothing to any other
  path, to an unknown token, or while that frame's **Use HA images** is off.
  By default it also answers only requests from the local network; turn off
  **Serve images to the local network only** in the integration options if
  your frame reaches Home Assistant through a public address.
- **Each frame gets its own picture.** The image view served the first
  frame's media source to every frame; with the token it serves each frame
  the source selected on that frame.
- **Turning off Use HA images gives the frame its image URL back.** Turning
  it on replaced the frame's image URL for good; turning it off now restores
  the URL the frame had before.

### Upgrading

Frames that use HA images are sent their new URL automatically. A sleeping
frame gets it at its next wake, and may miss that one rotation, since it
fetches the old address before the new one arrives.

## v2.12.1

### Fixed

- **Security: the frame password was sent to GitHub.** Since v2.12.0 the
  Firmware update entity fetched its release notes from the GitHub API through
  the same session that authenticates to the frame, so a frame with a password
  had its Basic `Authorization` header included in that request. GitHub does
  not act on it and answered normally, so nothing was observed to break, but
  the credential left the LAN on every release-notes view. The header is now
  attached only to requests under the frame's own URL, and the GitHub request
  goes through Home Assistant's plain session. Change the frame password if
  you opened the update dialog on v2.12.0 and want to be safe.

## v2.12.0

### Added

- **Firmware update entity.** The frame's firmware now shows up as a
  standard Home Assistant `update` entity (**Firmware**): installed and
  latest version, the release notes from GitHub in the update dialog, an
  **Install** button that runs the frame's OTA update, and install
  progress while it runs. It works with the Settings > Updates page and
  update notifications like any other device. The versions are cached in
  the config entry, so the entity is usable right after a Home Assistant
  restart while the frame is still asleep.

- **Current image survives a restart.** The last picture the frame
  displayed is saved under Home Assistant's storage directory and shown
  again after a restart, instead of a blank image until the frame's next
  rotation. The file is removed when the frame is removed from Home
  Assistant.

### Changed

- The **Update firmware** button is replaced by the update entity above
  and removed. The **Current version**, **Latest version** and **OTA
  state** sensors are deprecated: existing installs keep them, new installs
  get them disabled by default, and a later release removes them.
  - **Breaking:** automations and dashboards that press
    `button.esp32_photoframe_update_firmware` must switch to the
    `update.install` service on `update.esp32_photoframe_firmware`; the
    old button's registry entry is removed automatically on upgrade.
- The **Current image** entity only updates when the picture actually
  changed. A frame that re-serves the same image on check-in no longer
  bumps the image timestamp, so dashboards and the media browser stop
  refetching an unchanged picture.

### Fixed

- Restore the last reported battery percentage when Home Assistant restarts
  while the photo frame is asleep, instead of showing an unknown value until
  the frame's next refresh.

## v2.11.0

### Added

- **Frame password.** A frame with password protection enabled on its
  HTTP API (firmware newer than v2.18.0) can now be used from Home
  Assistant. Enter the password at setup (**Frame password**; blank, the
  default, means none) or later from the integration's **Configure**
  button, which applies it to the running integration without a reload. A
  wrong password at setup is reported as *invalid_auth* rather than as a
  connection failure. Known gap: a password enabled or changed on the frame
  after setup shows the frame as *unavailable* until the new password is
  entered under **Configure** — there is no re-authentication prompt yet.

### Changed

- **Time zone follows DST.** The **Timezone offset** number entity is
  replaced by a **Time zone** text entity
  (`text.esp32_photoframe_time_zone`) that takes either an IANA zone name
  (`Europe/Berlin`, `America/New_York`) or a full POSIX TZ rule
  (`EST5EDT,M3.2.0,M11.1.0`). The firmware applies the rule with `tzset()`,
  so an hours-based rotation schedule now stays on local time across the
  DST changeover instead of drifting by an hour twice a year
  (esp32-photoframe #128). A name is resolved through the tz database Home
  Assistant itself runs on, so it tracks tzdata updates and `UTC` or links
  such as `US/Pacific` work too; a built-in table of 466 zones supplies the
  names shown back whenever the frame's rule matches one, and the fallback
  rules. A fixed offset such as `UTC-8` or a custom rule is shown as-is,
  and the raw rule is always in the entity's `posix_rule` attribute. The
  frame can only hold one recurring rule, so a name is accepted only when
  the tz database's rule for it gives the right clock at every point in the
  next two years — a zone with an enacted change not yet in force is
  refused, naming the rule and the date it goes wrong, rather than applied
  silently an hour off. A divergence further out (`Asia/Gaza` and
  `Asia/Hebron` follow the Islamic calendar and first differ in 2036) is
  accepted; the rule will need re-entering when it comes due. A **Use Home
  Assistant time zone** button sets the frame to Home Assistant's own zone
  in one press. The old number entity read any DST rule as `0` and
  overwrote it with a fixed offset when set.
  - **Breaking:** dashboards and automations referencing
    `number.esp32_photoframe_timezone_offset` must be updated to the new
    `text.esp32_photoframe_time_zone` entity; the old registry entry is
    removed automatically on upgrade. A frame left on a fixed offset such
    as `UTC-8` keeps it, and the text entity shows it as-is.

### Fixed

- The manifest no longer lists `aiohttp` as a requirement. Home Assistant
  ships it, and hassfest rejects integrations that pin it themselves, so
  validation had been failing since 2026-10-01.

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
