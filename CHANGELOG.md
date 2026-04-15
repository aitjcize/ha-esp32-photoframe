# Changelog

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
  device's full config so any edits made via the device web UI are
  reflected in HA entities.

### Changed
- Config controls stay available through transient polling failures
  (e.g. a poll landing during a post-auto-rotate sleep cycle) — they no
  longer flip to unavailable just because `last_update_success` toggled.
- `_fetch_config` and the top-level update path now also catch
  `asyncio.TimeoutError` and `OSError`, so partial-response or timeout
  scenarios don't mark the coordinator as failed.

### Disabled states
- Config controls are still disabled when there is genuinely no state to
  show — e.g. after an HA restart while the device is offline and with
  no pending edits queued.
