"""Independent comparison outputs, without writes to the associated Person."""

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

if TYPE_CHECKING:
    from . import PresenceCoordinator
from homeassistant.util import dt as dt_util

from .entity import presence_device_info


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        PresenceSensor(entry, kind, label)
        for kind, label in (
            ("whereabouts", "Whereabouts"),
            ("dashboard_whereabouts", "Dashboard whereabouts"),
            ("last_known_whereabouts", "Last known whereabouts"),
            ("last_observation_time", "Last observation time"),
            ("location", "Location"),
            ("room", "Room"),
            ("selected", "Selected device"),
            ("reason", "Decision"),
        )
    )


class PresenceSensor(CoordinatorEntity["PresenceCoordinator"], SensorEntity):
    coordinator: PresenceCoordinator
    _attr_has_entity_name = True
    _attr_should_poll = False
    _unrecorded_attributes = frozenset({"evidence", "observed_at"})

    def __init__(self, entry, kind, label):
        super().__init__(entry.runtime_data)
        self._attr_device_info = presence_device_info(entry)
        self.kind = kind
        if kind in ("last_known_whereabouts", "last_observation_time"):
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            self._attr_entity_registry_enabled_default = False
        if kind == "last_observation_time":
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_unique_id = f"{entry.entry_id}_{kind}"
        self._attr_name = label
        self._attr_icon = "mdi:account-search" if kind != "room" else "mdi:floor-plan"

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if self.kind == "last_observation_time":
            self.async_on_remove(
                self.coordinator.add_timing_listener(self.async_write_ha_state)
            )

    @property
    def native_value(self):
        result = self.coordinator.data
        if self.kind == "dashboard_whereabouts":
            return self.coordinator.dashboard_whereabouts()["value"]
        if self.kind == "whereabouts":
            return self.coordinator.whereabouts().value
        if self.kind == "last_known_whereabouts":
            return self.coordinator.last_known_whereabouts
        if self.kind == "last_observation_time":
            at = self.coordinator.last_observation_time
            return dt_util.utc_from_timestamp(at) if at is not None else None
        if self.kind == "selected":
            return next(
                (
                    d["name"]
                    for d in self.coordinator.config["devices"]
                    if d["key"] == result.selected
                ),
                None,
            )
        if self.kind == "location" and result.zone_id and result.zone_id != "zone.home":
            return self.coordinator.places.zone_name(result.zone_id) or "not_home"
        if self.kind == "reason":
            return self.coordinator.explanation()
        return getattr(result, self.kind)

    @property
    def extra_state_attributes(self):
        if self.kind == "dashboard_whereabouts":
            return self.coordinator.dashboard_whereabouts()["attributes"]
        if self.kind == "whereabouts":
            return self.coordinator.whereabouts().attributes
        return self.coordinator.details()
