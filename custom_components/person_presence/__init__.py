"""Person Presence: read-only device inference with independent comparison entities."""

import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import DOMAIN, PLATFORMS
from .engine import Resolver, Result
from .history import restore_record
from .inputs import SOURCE_FIELDS, observe, validate_config
from .places import PlaceCatalog
from .repairs import remove_issues, sync_missing_sources
from .sources import SourceCatalog
from .whereabouts import project_whereabouts

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Set up one person's independent comparison entities."""
    config = validate_config({**entry.data, **entry.options})
    runtime = PresenceCoordinator(hass, entry, config)
    entry.runtime_data = runtime
    await runtime.async_load_history()
    await runtime.async_refresh_at(dt_util.utcnow())
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    runtime.start()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        entry.runtime_data.stop()
        await entry.runtime_data.async_save_history()
        return
    raise ConfigEntryError("Unable to unload Person Presence platforms")


class PresenceCoordinator(DataUpdateCoordinator[Result]):
    """Read existing states only; expire evidence even when sources stop reporting."""

    def __init__(self, hass, entry, config):
        super().__init__(hass, _LOGGER, name=DOMAIN, config_entry=entry)
        self.config = config
        self.entry = entry
        self._published_signature: Result | None = None
        self._timing_listeners: set[Callable[[], None]] = set()
        self.resolver = Resolver(
            settle=config["settle"],
            gps_age=config["gps_age"],
            room_age=config["room_age"],
        )
        self.last_known_whereabouts: str | None = None
        self.last_observation_time: float | None = None
        self.running = False
        self._stopped = False
        self.dashboard_history: dict | None = None
        self.history_store: Store[dict] = Store(
            hass,
            1,
            f"{DOMAIN}.{entry.entry_id}.history",
            private=True,
            atomic_writes=True,
        )
        self._history_save_at = 0.0
        self.catalog = SourceCatalog.from_hass(hass)
        self.places = PlaceCatalog.from_hass(hass)
        self.history_sources = {
            device[field]
            for device in config["devices"]
            for field in ("tracker", "room")
            if device.get(field)
        }
        self._unsub = []
        self.sources = {
            device[field]
            for device in config["devices"]
            for field in SOURCE_FIELDS
            if device.get(field)
        }

    async def async_load_history(self):
        try:
            data = await self.history_store.async_load()
        except OSError:
            _LOGGER.warning(
                "Unable to load dashboard history; current inference continues"
            )
            return
        self.dashboard_history = restore_record(
            data,
            self.config["person"],
            self.history_sources,
            dt_util.utcnow().timestamp(),
        )

    async def async_save_history(self):
        try:
            await self.history_store.async_save(self.dashboard_history or {})
        except OSError:
            _LOGGER.warning(
                "Unable to save dashboard history; current inference continues"
            )

    def dashboard_whereabouts(self):
        current = self.whereabouts()
        value = current.value
        historical = value is None and self.dashboard_history is not None
        record = self.dashboard_history if historical else None
        return {
            "value": (record["value"][:242] + " (last known)") if record else value,
            "attributes": {
                "freshness": "last_known"
                if historical
                else "current"
                if value is not None
                else "unknown",
                "current_presence": current.attributes["presence"],
                "observed_at": dt_util.utc_from_timestamp(
                    record["observed_at"]
                ).isoformat()
                if record
                else None,
                "last_known_value": record["value"] if record else None,
                "source_entity_id": record["source_entity_id"]
                if record
                else current.attributes["source_entity_id"],
                "settling": current.attributes["settling"],
            },
        }

    @callback
    def start(self):
        self.running = True
        self._stopped = False
        self._unsub.append(
            async_track_state_change_event(
                self.hass, self.sources, self._source_changed
            )
        )
        self._unsub.append(
            async_track_time_interval(
                self.hass, self.async_refresh_at, timedelta(seconds=5)
            )
        )

        for event_type in (
            "entity_registry_updated",
            "device_registry_updated",
            "area_registry_updated",
        ):
            self._unsub.append(
                self.hass.bus.async_listen(event_type, self._registry_changed)
            )
        self._unsub.append(
            self.hass.bus.async_listen("state_changed", self._zone_changed)
        )

    @callback
    def _registry_changed(self, event):
        if self.running:
            self.catalog = SourceCatalog.from_hass(self.hass)
            self.places = PlaceCatalog.from_hass(self.hass)
            self._evaluate(dt_util.utcnow())

    @callback
    def _zone_changed(self, event):
        if self.running and event.data.get("entity_id", "").startswith("zone."):
            self.places = PlaceCatalog.from_hass(self.hass)
            self._evaluate(dt_util.utcnow())

    @callback
    def stop(self):
        self.running = False
        self._stopped = True
        for unsub in self._unsub:
            unsub()
        self._unsub.clear()

    @callback
    def _source_changed(self, event):
        if self.running:
            self._evaluate(dt_util.utcnow())

    async def async_refresh_at(self, now):
        if not self._stopped:
            self._evaluate(now)

    @callback
    def _evaluate(self, now):
        timestamp = now.timestamp()
        observations = [
            observe(
                device,
                self.hass.states.get,
                timestamp,
                self.hass.config.time_zone,
                self.config["signal_age"],
                self.config["max_accuracy"],
                catalog=self.catalog,
                places=self.places,
            )
            for device in self.config["devices"]
        ]
        previous_observation_time = self.last_observation_time
        result = self.resolver.update(observations, timestamp)
        projected = project_whereabouts(
            result,
            self.places,
            self.config["person"],
            {d["key"]: d["name"] for d in self.config["devices"]},
        )
        if projected.value is not None and not result.pending:
            self.last_known_whereabouts = projected.value
            self.last_observation_time = result.observed_at
        if (
            projected.value is not None
            and not result.pending
            and result.observed_at is not None
        ):
            record = restore_record(
                {
                    "value": projected.value,
                    "observed_at": result.observed_at,
                    "person_entity_id": self.config["person"],
                    "source_entity_id": result.source_entity_id,
                },
                self.config["person"],
                self.history_sources,
                timestamp,
            )
            if record is not None:
                previous = self.dashboard_history
                self.dashboard_history = record
                changed_place = previous is None or any(
                    previous[key] != record[key]
                    for key in ("value", "source_entity_id")
                )
                if changed_place or timestamp - self._history_save_at >= 60:
                    self._history_save_at = timestamp
                    self.history_store.async_delay_save(
                        lambda: self.dashboard_history or {}, 5
                    )
        sync_missing_sources(self.hass, self.entry, self.config)
        stable_evidence = {
            key: {
                k: v
                for k, v in item.items()
                if k not in ("gps_observed_at", "room_observed_at")
            }
            for key, item in result.evidence.items()
        }
        signature = replace(
            result, observed_at=None, room_at=None, evidence=stable_evidence
        )
        if signature != self._published_signature:
            self._published_signature = signature
            self.async_set_updated_data(result)
        else:
            self.data = result
            if self.last_observation_time != previous_observation_time:
                for listener in tuple(self._timing_listeners):
                    listener()

    def add_timing_listener(self, listener):
        self._timing_listeners.add(listener)
        return lambda: self._timing_listeners.discard(listener)

    def details(self):
        result = self.data
        names = {d["key"]: d["name"] for d in self.config["devices"]}
        return {
            "person": self.config["person"],
            "comparison_mode": True,
            "selected_device": names.get(result.selected),
            "selected_device_key": result.selected,
            "reason": self.explanation(),
            "confidence": result.confidence,
            "settling": result.pending,
            "observed_at": dt_util.utc_from_timestamp(result.observed_at).isoformat()
            if result.observed_at is not None
            else None,
            "evidence": {names.get(k, k): v for k, v in result.evidence.items()},
        }

    def explanation(self):
        reason = self.data.reason
        for device in self.config["devices"]:
            reason = reason.replace(device["key"], device["name"])
        return reason

    def whereabouts(self):
        return project_whereabouts(
            self.data,
            self.places,
            self.config["person"],
            {d["key"]: d["name"] for d in self.config["devices"]},
        )


async def async_remove_entry(hass, entry):
    remove_issues(hass, entry)
    await Store(
        hass, 1, f"{DOMAIN}.{entry.entry_id}.history", private=True, atomic_writes=True
    ).async_remove()
