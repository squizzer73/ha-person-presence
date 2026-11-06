"""Deterministic person inference. No Home Assistant imports or household data."""

from dataclasses import dataclass, field, replace
from math import isfinite


@dataclass(frozen=True)
class Observation:
    key: str
    priority: int
    worn: bool | None = None
    excluded: str | None = None
    location: str | None = None
    location_at: float | None = None
    room: str | None = None
    room_at: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    accuracy: float | None = None
    notes: tuple[str, ...] = ()
    area_id: str | None = None
    zone_id: str | None = None
    gps_source_entity_id: str | None = None
    room_source_entity_id: str | None = None
    timestamp_quality: str = "measurement"
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class Result:
    location: str | None = None
    room: str | None = None
    selected: str | None = None
    reason: str = "No fresh evidence"
    confidence: str = "unknown"
    observed_at: float | None = None
    room_at: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    accuracy: float | None = None
    evidence: dict = field(default_factory=dict)
    pending: bool = False
    context: str = "unknown"
    area_id: str | None = None
    zone_id: str | None = None
    source_entity_id: str | None = None
    wearing_status: str = "unconfirmed"

    @property
    def signature(self):
        return (
            self.location,
            self.room,
            self.selected,
            self.context,
            self.area_id,
            self.zone_id,
        )


def fresh(at: float | None, now: float, limit: float) -> bool:
    return at is not None and isfinite(at) and 0 <= now - at <= limit


class Resolver:
    """Hold stable transitions, while dropping expired or excluded sources immediately."""

    def __init__(self, *, settle=15, gps_age=300, room_age=60):
        self.settle = settle
        self.gps_age = gps_age
        self.room_age = room_age
        self.result = Result()
        self._pending = None
        self._pending_since = 0.0

    def update(self, observations: list[Observation], now: float) -> Result:
        evidence = {}
        candidates: list[Result] = []
        for obs in sorted(
            observations, key=lambda x: (x.worn is not True, x.priority, x.key)
        ):
            gps = bool(obs.location) and fresh(obs.location_at, now, self.gps_age)
            room = bool(obs.room) and fresh(obs.room_at, now, self.room_age)
            reasons = list(obs.reason_codes)
            excluded_codes = {"charging": "charging", "not worn": "not_worn"}
            if obs.excluded:
                reasons.append(
                    excluded_codes.get(obs.excluded, "eligibility_unconfirmed")
                )
            if obs.location and not gps:
                reasons.append("stale_location")
            if obs.timestamp_quality != "measurement":
                reasons.append("timestamp_quality_limited")
            evidence[obs.key] = {
                "priority": obs.priority,
                "worn": obs.worn,
                "excluded": obs.excluded,
                "gps_fresh": gps,
                "room_fresh": room,
                "gps_observed_at": obs.location_at,
                "gps_source_entity_id": obs.gps_source_entity_id,
                "room_source_entity_id": obs.room_source_entity_id,
                "room_observed_at": obs.room_at,
                "timestamp_quality": obs.timestamp_quality,
                "notes": list(obs.notes),
                "reasons": reasons,
            }
            if obs.excluded:
                continue
            conflict = (
                gps
                and room
                and obs.location != "home"
                and obs.location_at == obs.room_at
            )
            if conflict:
                reasons.append("conflicting_evidence")
            if not gps and not room:
                reasons.append("no_fresh_evidence")
                if obs.worn is True and not candidates:
                    candidates.append(
                        Result(reason=f"{obs.key} is worn but has no fresh location")
                    )
                continue
            if candidates:
                reasons.append("lower_preference")
                continue
            if conflict:
                candidates.append(
                    Result(reason="Conflicting room and geographical evidence")
                )
                continue
            use_room = room and (
                not gps
                or (
                    obs.room_at is not None
                    and obs.location_at is not None
                    and obs.room_at > obs.location_at
                )
                or obs.location == "home"
            )
            location = "home" if use_room else obs.location
            selected_room = obs.room if room and location == "home" else None
            coordinates = gps and obs.location == location
            reasons.append("selected")
            candidates.append(
                Result(
                    location=location,
                    room=selected_room,
                    selected=obs.key,
                    reason=f"Following {obs.key}: "
                    + (
                        "worn device"
                        if obs.worn is True
                        else "highest preference with fresh evidence"
                    ),
                    confidence="corroborated"
                    if gps and room and obs.location == "home"
                    else "single_source",
                    observed_at=obs.room_at if use_room else obs.location_at,
                    room_at=obs.room_at if selected_room else None,
                    latitude=obs.latitude if coordinates else None,
                    longitude=obs.longitude if coordinates else None,
                    accuracy=obs.accuracy if coordinates else None,
                    context="room"
                    if selected_room
                    else "home"
                    if location == "home"
                    else "away"
                    if location in ("not_home", "away")
                    else "zone",
                    area_id=obs.area_id if selected_room else None,
                    zone_id="zone.home" if location == "home" else obs.zone_id,
                    source_entity_id=obs.room_source_entity_id
                    if use_room
                    else obs.gps_source_entity_id,
                    wearing_status="confirmed" if obs.worn is True else "unconfirmed",
                )
            )
        desired = replace(candidates[0] if candidates else Result(), evidence=evidence)
        current = self.result
        selected = next((o for o in observations if o.key == current.selected), None)
        valid_current = (
            selected is not None
            and not selected.excluded
            and fresh(
                current.observed_at,
                now,
                self.room_age if current.room else self.gps_age,
            )
        )
        if selected is not None and current.location == "home":
            positive_away = selected.location not in (None, "home") and fresh(
                selected.location_at, now, self.gps_age
            )
            if positive_away or "local_guard_away" in selected.reason_codes:
                valid_current = False
        if desired.location is None or desired.signature == current.signature:
            self._pending = None
            self.result = desired
        else:
            if desired.signature != self._pending:
                self._pending = desired.signature
                self._pending_since = now
            if now - self._pending_since >= self.settle:
                self.result = desired
                self._pending = None
            else:
                held = current if valid_current else Result()
                self.result = replace(
                    held,
                    pending=True,
                    evidence=evidence,
                    reason=f"Settling: {desired.reason}",
                )
        return self.result
