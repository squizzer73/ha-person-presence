"""Compact current whereabouts for dashboards, notifications and automations."""

from collections.abc import Mapping
from dataclasses import dataclass

from .engine import Result
from .places import PlaceCatalog


@dataclass(frozen=True)
class Whereabouts:
    value: str | None
    attributes: dict


def project_whereabouts(
    result: Result,
    places: PlaceCatalog,
    person_entity_id: str,
    device_names: Mapping[str, str],
) -> Whereabouts:
    location = result.location
    context = "unknown"
    presence = "unknown"
    value = None
    area_id = result.area_id if result.area_id in places.areas else None
    zone_id = result.zone_id if result.zone_id in places.zones else None
    if location == "home":
        presence = "home"
        zone_id = "zone.home" if "zone.home" in places.zones else None
        if result.room:
            context = "room"
            value = places.area_name(area_id) or result.room
        else:
            context = "home"
            value = "Home"
    elif location is not None:
        presence = "away"
        if zone_id and zone_id != "zone.home":
            context = "zone"
            value = places.zone_name(zone_id)
        else:
            context = "away"
            value = "Away"
    return Whereabouts(
        value,
        {
            "person_entity_id": person_entity_id,
            "presence": presence,
            "context": context,
            "area_id": area_id if context == "room" else None,
            "zone_id": zone_id,
            "selected_device_id": result.selected,
            "selected_device_name": device_names.get(result.selected)
            if result.selected is not None
            else None,
            "source_entity_id": result.source_entity_id,
            "confidence": result.confidence,
            "wearing_status": result.wearing_status,
            "settling": result.pending,
        },
    )
