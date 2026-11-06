"""Canonical place identities; labels may change independently of automations."""

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt


@dataclass(frozen=True)
class Zone:
    entity_id: str
    name: str
    latitude: float
    longitude: float
    radius: float
    passive: bool = False


class PlaceCatalog:
    def __init__(self, areas=None, zones=()):
        self.areas = dict(areas or {})
        self.zones = {z.entity_id: z for z in zones}

    def area_name(self, area_id):
        return self.areas.get(area_id)

    def zone_name(self, zone_id):
        zone = self.zones.get(zone_id)
        return zone.name if zone else None

    def resolve_zone(self, latitude, longitude, reported_zone_ids=()):
        matches = []
        for zone in self.zones.values():
            if zone.passive:
                continue
            distance = float("inf")
            if latitude is not None and longitude is not None:
                dlat, dlon = (
                    radians(latitude - zone.latitude),
                    radians(longitude - zone.longitude),
                )
                a = (
                    sin(dlat / 2) ** 2
                    + cos(radians(latitude))
                    * cos(radians(zone.latitude))
                    * sin(dlon / 2) ** 2
                )
                distance = 6371000 * 2 * asin(sqrt(min(1, max(0, a))))
            if distance <= zone.radius or zone.entity_id in reported_zone_ids:
                matches.append(zone)
        matches.sort(key=lambda z: (z.entity_id != "zone.home", z.radius, z.entity_id))
        return matches[0].entity_id if matches else None

    @classmethod
    def from_hass(cls, hass):
        from homeassistant.helpers import area_registry

        areas = {a.id: a.name for a in area_registry.async_get(hass).areas.values()}
        zones = []
        for state in hass.states.async_all("zone"):
            a = state.attributes
            try:
                zones.append(
                    Zone(
                        state.entity_id,
                        state.name,
                        float(a["latitude"]),
                        float(a["longitude"]),
                        float(a["radius"]),
                        bool(a.get("passive")),
                    )
                )
            except KeyError, TypeError, ValueError:
                continue
        return cls(areas, zones)
