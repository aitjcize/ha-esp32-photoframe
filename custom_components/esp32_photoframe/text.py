"""Text platform for ESP32 PhotoFrame."""

from __future__ import annotations

import re
from typing import Any

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PendingConfigEntityMixin, PhotoFrameCoordinator
from .dynamic_entities import async_setup_firmware_gated_entities
from .timezones import (
    OPTION_TIMEZONE_NAME,
    PRINTABLE_ASCII_RE,
    TIMEZONE_MAX_LEN,
    async_resolve_timezone,
    get_timezone_rules,
    remember_timezone_name,
)

# Firmware limits for the rotation schedule (main/config.h)
MAX_CRON_RULES = 7
CRON_RULE_MAX_LEN = 64  # rules must be shorter than this
# One simplified 3-field cron rule: three whitespace-separated groups of
# digits / * / , / - / step. Semantic validation (ranges, steps) happens on
# the device; this catches the structural typos cheaply.
_CRON_RULE_RE = re.compile(r"^[0-9*,/-]+[ \t]+[0-9*,/-]+[ \t]+[0-9*,/-]+$")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the text platform."""
    coordinator: PhotoFrameCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            PhotoFrameImageUrlText(coordinator, entry),
            PhotoFrameHaUrlText(coordinator, entry),
            PhotoFrameTimezoneText(coordinator, entry),
            # Advanced network settings: NTP is supported by all firmware
            # versions, so it is not gated.
            PhotoFrameNtpServerText(coordinator, entry),
        ]
    )

    # Advanced network settings (#43): static IP / DNS override exist only on
    # firmware that reports ip_mode; on older firmware these entities are not
    # created (and are removed if the device downgrades).
    async_setup_firmware_gated_entities(
        hass,
        coordinator,
        async_add_entities,
        "text",
        "ip_mode",
        [
            lambda: PhotoFrameStaticIpText(coordinator, entry),
            lambda: PhotoFrameStaticNetmaskText(coordinator, entry),
            lambda: PhotoFrameStaticGatewayText(coordinator, entry),
            lambda: PhotoFrameDnsServerText(coordinator, entry),
        ],
    )

    # Cron firmware only: the rotation schedule replaced the legacy sleep
    # schedule, so this appears only while the device reports rotate_cron.
    async_setup_firmware_gated_entities(
        hass,
        coordinator,
        async_add_entities,
        "text",
        "rotate_cron",
        [lambda: PhotoFrameRotationScheduleText(coordinator, entry)],
    )


class PhotoFrameRotationScheduleText(PendingConfigEntityMixin, CoordinatorEntity, TextEntity):
    """Rotation schedule (cron) text entity for PhotoFrame.

    The schedule is a list of simplified 3-field cron rules
    ("minute hour day-of-week"). Multiple rules are shown/edited as a single
    "; "-separated string, e.g. "0 */12 *" or "0 9 1-5; 0 18 0,6".
    """

    _attr_has_entity_name = True
    _attr_native_max = 255
    _attr_pattern = r"^[0-9*,/\- \t]+(;[0-9*,/\- \t]+)*$"
    _config_key = "rotate_cron"
    _default_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_rotation_schedule"
        self._attr_name = "Rotation schedule"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """Unavailable on pre-cron firmware, which ignores rotate_cron writes."""
        if not super().available:
            return False
        config = self.coordinator.data.get("config", {})
        return "rotate_cron" in config or self.coordinator.is_key_pending("rotate_cron")

    def _rules(self) -> list[str]:
        config = self.coordinator.data.get("config", {})
        rules = config.get("rotate_cron") or []
        if isinstance(rules, str):
            rules = [rules]
        return [str(r).strip() for r in rules if str(r).strip()]

    @property
    def native_value(self) -> str | None:
        """Return the rotation schedule as a "; "-joined cron string."""
        joined = "; ".join(self._rules())
        if len(joined) > 255:
            # A TextEntity state longer than native_max raises; the full rule
            # list stays readable via the `rules` attribute, and the ellipsis
            # fails the input pattern so a truncated value can't be saved
            # back by accident.
            return joined[:254] + "…"
        return joined

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Expose the schedule as a proper list alongside the joined state."""
        attrs = dict(super().extra_state_attributes or {})
        attrs["rules"] = self._rules()
        return attrs

    async def async_set_value(self, value: str) -> None:
        """Set the rotation schedule from a "; "/newline-separated cron string."""
        rules = [r.strip() for r in value.replace("\n", ";").split(";")]
        rules = [r for r in rules if r]
        if not rules:
            raise ServiceValidationError("Schedule must contain at least one cron rule")
        if len(rules) > MAX_CRON_RULES:
            raise ServiceValidationError(f"At most {MAX_CRON_RULES} schedule rules are supported")
        for rule in rules:
            if len(rule) >= CRON_RULE_MAX_LEN:
                raise ServiceValidationError(
                    f"Cron rule too long (max {CRON_RULE_MAX_LEN - 1} chars): {rule}"
                )
            if not _CRON_RULE_RE.match(rule):
                raise ServiceValidationError(
                    f"Not a 3-field cron rule ('minute hour day-of-week'): {rule}"
                )
        await self.coordinator.async_set_config({"rotate_cron": rules})


class PhotoFrameImageUrlText(PendingConfigEntityMixin, CoordinatorEntity, TextEntity):
    """Image URL text entity for PhotoFrame."""

    _attr_has_entity_name = True
    _attr_available = True  # Always editable, even when device is offline
    _config_key = "image_url"
    _default_icon = "mdi:link"

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_image_url"
        self._attr_name = "Image URL"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> str | None:
        """Return the current image URL."""
        config = self.coordinator.data.get("config", {})
        return config.get("image_url", "")

    async def async_set_value(self, value: str) -> None:
        """Set the image URL."""
        await self.coordinator.async_set_config({"image_url": value})


class PhotoFrameHaUrlText(PendingConfigEntityMixin, CoordinatorEntity, TextEntity):
    """Home Assistant URL text entity for PhotoFrame."""

    _attr_has_entity_name = True
    _attr_available = True  # Always editable, even when device is offline
    _config_key = "ha_url"
    _default_icon = "mdi:home-assistant"

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_ha_url"
        self._attr_name = "Home Assistant URL"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> str | None:
        """Return the current HA URL."""
        config = self.coordinator.data.get("config", {})
        return config.get("ha_url", "")

    async def async_set_value(self, value: str) -> None:
        """Set the HA URL."""
        await self.coordinator.async_set_config({"ha_url": value})


class PhotoFrameTimezoneText(PendingConfigEntityMixin, CoordinatorEntity, TextEntity):
    """Time zone text entity for PhotoFrame (esp32-photoframe #128).

    The device stores a POSIX TZ rule and applies it with tzset(), so a rule
    with DST transitions ("EST5EDT,M3.2.0,M11.1.0") keeps an hours-based
    rotation schedule on local time all year. The entity accepts an IANA zone
    name, resolved through the tz database Home Assistant itself runs on
    (see timezones.TimezoneRules), or a raw POSIX rule, and shows a zone
    name back whenever the stored rule is one of a table zone. Many zones
    share a rule, so the name shown is the one last set here, else Home
    Assistant's own zone, else the table's first match; the ``posix_rule``
    attribute always carries what the device actually has.
    """

    _attr_has_entity_name = True
    _attr_available = True  # Always editable, even when device is offline
    _attr_native_max = TIMEZONE_MAX_LEN - 1
    _attr_pattern = PRINTABLE_ASCII_RE.pattern
    _config_key = "timezone"
    _default_icon = "mdi:map-clock"

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_timezone"
        self._attr_name = "Time zone"
        self._attr_device_info = coordinator.device_info

    def _rule(self) -> str | None:
        """The stored POSIX rule, or None when there is no usable value."""
        config = self.coordinator.data.get("config", {})
        rule = config.get("timezone")
        if not isinstance(rule, str) or not rule:
            return None
        # TextEntity refuses to publish a state that fails its own pattern or
        # length, so never hand it one; the device can only have got such a
        # value from a raw PATCH, and it isn't a working time zone anyway.
        if len(rule) >= TIMEZONE_MAX_LEN or not PRINTABLE_ASCII_RE.match(rule):
            return None
        return rule

    @property
    def native_value(self) -> str | None:
        """Return the IANA name for the stored rule, or the rule itself."""
        rule = self._rule()
        if rule is None:
            return None
        preferred = [self._entry.options.get(OPTION_TIMEZONE_NAME), self.hass.config.time_zone]
        return get_timezone_rules(self.hass).name_for_rule(rule, preferred) or rule

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Expose the raw POSIX rule alongside the (possibly named) state."""
        attrs = dict(super().extra_state_attributes or {})
        attrs["posix_rule"] = self._rule()
        return attrs

    async def async_set_value(self, value: str) -> None:
        """Set the time zone from an IANA name or a POSIX TZ rule."""
        try:
            name, rule = await async_resolve_timezone(self.hass, value)
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
        # The name first: async_set_config notifies the entities at once, and
        # native_value prefers the remembered name when zones share the rule.
        # Should the frame then reject the rule, the name is ignored, since
        # it is only used while its rule is the one stored.
        remember_timezone_name(self.hass, self._entry, name)
        await self.coordinator.async_set_config({"timezone": rule})


class PhotoFrameNtpServerText(PendingConfigEntityMixin, CoordinatorEntity, TextEntity):
    """NTP server text entity for PhotoFrame."""

    _attr_has_entity_name = True
    _attr_available = True  # Always editable, even when device is offline
    _config_key = "ntp_server"
    _default_icon = "mdi:clock-outline"

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_ntp_server"
        self._attr_name = "NTP server"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> str | None:
        """Return the current NTP server."""
        config = self.coordinator.data.get("config", {})
        return config.get("ntp_server", "")

    async def async_set_value(self, value: str) -> None:
        """Set the NTP server."""
        await self.coordinator.async_set_config({"ntp_server": value})


class _PhotoFrameNetworkText(PendingConfigEntityMixin, CoordinatorEntity, TextEntity):
    """Base for the advanced-network text entities (#43).

    Values are dotted IPv4 strings; the firmware validates them and rejects the
    save with an error on a malformed address.
    """

    _attr_has_entity_name = True
    _attr_available = True  # Always editable, even when device is offline
    _default_icon = "mdi:ip-network"

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{self._config_key}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> str | None:
        """Return the current value."""
        config = self.coordinator.data.get("config", {})
        return config.get(self._config_key, "")

    async def async_set_value(self, value: str) -> None:
        """Set the value."""
        await self.coordinator.async_set_config({self._config_key: value})


class _PhotoFrameStaticOnlyText(_PhotoFrameNetworkText):
    """Static-address field, unavailable (grayed out) while the mode is DHCP.

    HA has no state-conditional show/hide for entities, so unavailability is
    the standard way to signal that a field doesn't currently apply. The check
    reads the effective (pending-merged) config, so flipping the IP mode select
    to "static" enables these fields immediately — before the device has even
    seen the change — letting the user fill them in as part of the same batch.
    """

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        config = self.coordinator.data.get("config", {})
        return config.get("ip_mode", "dhcp") == "static"


class PhotoFrameStaticIpText(_PhotoFrameStaticOnlyText):
    """Static IP address text entity."""

    _config_key = "static_ip"

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator, entry)
        self._attr_name = "Static IP address"


class PhotoFrameStaticNetmaskText(_PhotoFrameStaticOnlyText):
    """Static netmask text entity."""

    _config_key = "static_netmask"

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator, entry)
        self._attr_name = "Static netmask"


class PhotoFrameStaticGatewayText(_PhotoFrameStaticOnlyText):
    """Static gateway text entity."""

    _config_key = "static_gateway"

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator, entry)
        self._attr_name = "Static gateway"


class PhotoFrameDnsServerText(_PhotoFrameNetworkText):
    """DNS server override text entity."""

    _config_key = "dns_server"
    _default_icon = "mdi:dns"

    def __init__(self, coordinator: PhotoFrameCoordinator, entry: ConfigEntry) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator, entry)
        self._attr_name = "DNS server"
