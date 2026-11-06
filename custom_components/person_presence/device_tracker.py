"""Optional tracker. Disabled by default and never automatically assigned to Person."""

from typing import TYPE_CHECKING

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

if TYPE_CHECKING:
    from . import PresenceCoordinator

from .entity import presence_device_info


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([PresenceTracker(entry)])


class PresenceTracker(CoordinatorEntity["PresenceCoordinator"], TrackerEntity):
    coordinator: PresenceCoordinator
    _attr_has_entity_name = True
    _attr_entity_registry_enabled_default = False
    _attr_should_poll = False
    _attr_source_type = SourceType.GPS

    def __init__(self, entry):
        super().__init__(entry.runtime_data)
        self._attr_device_info = presence_device_info(entry)
        self._attr_unique_id = f"{entry.entry_id}_tracker"
        self._attr_name = "Tracker"

    @property
    def in_zones(self):
        location = self.coordinator.data.location
        if location is None:
            return None
        if location == "home":
            return ["zone.home"]
        return [
            s.entity_id
            for s in self.hass.states.async_all("zone")
            if s.name == location or s.entity_id == location
        ]

    @property
    def latitude(self):
        return self.coordinator.data.latitude

    @property
    def longitude(self):
        return self.coordinator.data.longitude

    @property
    def location_accuracy(self):
        return self.coordinator.data.accuracy or 0

    @property
    def extra_state_attributes(self):
        return self.coordinator.details()
