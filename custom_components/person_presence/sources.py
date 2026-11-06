"""Capability-based candidate choices; suggestions never establish device identity."""

from dataclasses import dataclass
from datetime import datetime

from .inputs import is_position_source, is_string_room_source, is_worn_source


@dataclass(frozen=True)
class SourceSnapshot:
    entity_id: str
    state: str
    attributes: dict
    last_reported: datetime
    platform: str = ""
    device_id: str | None = None

    @property
    def domain(self):
        return self.entity_id.split(".", 1)[0]

    @property
    def last_updated(self):
        return self.last_reported


@dataclass(frozen=True)
class Candidate:
    entity_id: str
    role: str
    provider: str
    state_summary: str
    basis: str = "capability"
    warnings: tuple[str, ...] = ()


class SourceCatalog:
    def __init__(self, snapshots=()):
        self.snapshots = {s.entity_id: s for s in snapshots}

    def get_state(self, entity_id):
        return self.snapshots.get(entity_id)

    def supports(self, source, role):
        a = source.attributes
        if source.platform == "person_presence":
            return False
        value = source.state.lower().replace(" ", "").replace("_", "")
        if role == "tracker":
            return (
                source.domain == "device_tracker"
                and is_position_source(source)
                and (
                    a.get("source_type") == "gps"
                    or a.get("tracking_type") == "position"
                    or "latitude" in a
                    and "longitude" in a
                )
            )
        if role == "local_tracker":
            return source.domain == "device_tracker" and (
                a.get("tracking_type") == "connection"
                or a.get("source_type") in ("bluetooth", "bluetooth_le", "router")
                or source.platform in ("bermuda", "private_ble_device")
            )
        if role == "room":
            return is_string_room_source(source.entity_id, source) and (
                source.platform == "bermuda"
                and source.entity_id.endswith("_area")
                or source.platform == "neonplan3d"
                and source.entity_id.endswith("_room")
                or bool(a.get("area_id"))
                and not a.get("unit_of_measurement")
            )
        if role == "charging":
            return (
                source.domain in ("sensor", "binary_sensor", "input_boolean")
                and a.get("device_class") != "battery"
                and not a.get("unit_of_measurement")
                and (
                    a.get("device_class") == "battery_charging"
                    or value
                    in ("charging", "charged", "full", "notcharging", "discharging")
                    or "charging" in source.entity_id
                )
            )
        if role == "worn":
            return is_worn_source(source.entity_id, source)
        if role == "timestamp_entity":
            return source.domain == "sensor" and (
                a.get("device_class") == "timestamp"
                or any(k in a for k in ("located", "last_located", "last_seen"))
            )
        return False

    def candidates(self, role, *, current_entity_id=None):
        result = [
            Candidate(s.entity_id, role, s.platform, s.state)
            for s in self.snapshots.values()
            if self.supports(s, role)
        ]
        result.sort(key=lambda c: c.entity_id)
        if current_entity_id and current_entity_id not in {c.entity_id for c in result}:
            s = self.snapshots.get(current_entity_id)
            result.append(
                Candidate(
                    current_entity_id,
                    role,
                    s.platform if s else "",
                    s.state if s else "missing",
                    "configured",
                    ("manual_or_unavailable",),
                )
            )
        return result

    def suggestions(self, entity_id):
        seed = self.snapshots.get(entity_id)
        if not seed or not seed.device_id:
            return {}
        return {
            role: [
                c.entity_id
                for c in self.candidates(role)
                if self.snapshots[c.entity_id].device_id == seed.device_id
            ]
            for role in (
                "tracker",
                "room",
                "local_tracker",
                "charging",
                "worn",
                "timestamp_entity",
            )
        }

    @classmethod
    def from_hass(cls, hass):
        from homeassistant.helpers import entity_registry

        registry = entity_registry.async_get(hass)
        rows = []
        for s in hass.states.async_all():
            if s.domain not in (
                "device_tracker",
                "sensor",
                "binary_sensor",
                "input_boolean",
                "person",
            ):
                continue
            entry = registry.async_get(s.entity_id)
            rows.append(
                SourceSnapshot(
                    s.entity_id,
                    s.state,
                    dict(s.attributes),
                    s.last_reported,
                    entry.platform if entry else "",
                    entry.device_id if entry else None,
                )
            )
        return cls(rows)
