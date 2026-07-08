"""Entities that exist only while the firmware reports a given feature.

Some settings are firmware-generation specific: legacy firmware has a sleep
schedule (``sleep_schedule_enabled``), while cron firmware has a rotation
schedule (``rotate_cron``) instead. Registering both sets statically leaves the
inapplicable ones lingering as permanently *unavailable*. Instead we watch the
coordinator and add each set only while the device actually reports its key,
removing it again if the device transitions (e.g. an OTA from legacy to cron
firmware, or vice versa).
"""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import PhotoFrameCoordinator


@callback
def async_setup_firmware_gated_entities(
    hass: HomeAssistant,
    coordinator: PhotoFrameCoordinator,
    async_add_entities: AddEntitiesCallback,
    platform_domain: str,
    gate_key: str,
    factories: list[Callable[[], Entity]],
) -> None:
    """Add entities while the device reports ``gate_key``; remove them when it stops.

    * The entities are added the first time a fetched config contains
      ``gate_key`` and are removed from the entity registry once the device
      reports a config without it (e.g. after an OTA that changed the scheduling
      model). Removal is by ``unique_id`` against the registry, so it also cleans
      up orphans left by an earlier static registration of these entities.
    * Deep-sleep devices don't report their config until they next check in, so
      an empty config means "not seen yet" and is left untouched — we only act
      on a config we actually fetched. The coordinator keeps the last known
      config through sleep, so the key doesn't flap while the device dozes.
    """
    # Throwaway instances just to learn the unique_ids up front — constructing an
    # entity has no side effects until it's added to hass. We create fresh
    # instances when actually adding (an entity can't be re-added after removal).
    unique_ids = [factory().unique_id for factory in factories]
    added = False

    @callback
    def _sync() -> None:
        nonlocal added
        config = coordinator.data.get("config", {})
        if not config:
            return  # device asleep / never seen this session — decide later
        if gate_key in config:
            if not added:
                async_add_entities([factory() for factory in factories])
                added = True
        else:
            registry = er.async_get(hass)
            for unique_id in unique_ids:
                entity_id = registry.async_get_entity_id(platform_domain, DOMAIN, unique_id)
                if entity_id:
                    registry.async_remove(entity_id)
            added = False

    coordinator.async_add_listener(_sync)
    _sync()
