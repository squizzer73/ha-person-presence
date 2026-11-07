"""Validate user mappings and turn read-only HA states into timestamped evidence."""

import re
from collections.abc import Mapping
from datetime import UTC, datetime
from math import isfinite
from typing import Any, Protocol, TypeGuard
from zoneinfo import ZoneInfo

from .engine import Observation, fresh

DEFAULTS = {
    "gps_age": 300,
    "room_age": 60,
    "signal_age": 600,
    "settle": 15,
    "max_accuracy": 100,
}
SOURCE_FIELDS = (
    "tracker",
    "room",
    "local_tracker",
    "charging",
    "worn",
    "timestamp_entity",
)
INVALID = {"unknown", "unavailable", "none", "", "not_home", "away"}


def validate_config(config):
    """Validate both UI submissions and stored entries, including source domains."""
    result = {**DEFAULTS, **config}
    if "geocode" in config and not isinstance(config["geocode"], bool):
        raise ValueError("invalid_geocoder")
    if "place_lookup" in config:
        from .geocoding import validate_options

        if not isinstance(config["place_lookup"], dict):
            raise ValueError("invalid_geocoder")
        result["place_lookup"] = validate_options(config["place_lookup"])
    if not str(result.get("name", "")).strip() or not re.fullmatch(
        r"person\.[a-z0-9_]+", result.get("person", "")
    ):
        raise ValueError("invalid_person")
    for key in DEFAULTS:
        value = result[key]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(value)
        ):
            raise ValueError("invalid_settings")
        if not (0 <= value <= 3600 if key == "settle" else 1 <= value <= 86400):
            raise ValueError("invalid_settings")
    devices = result.get("devices", [])
    if not devices:
        raise ValueError("no_devices")
    keys, names, trackers, priorities = set(), set(), set(), set()
    for device in devices:
        key = device.get("key")
        name = str(device.get("name", "")).strip()
        priority = device.get("priority")
        if (
            not isinstance(key, str)
            or not key
            or key in keys
            or not name
            or name.casefold() in names
            or isinstance(priority, bool)
            or not isinstance(priority, int)
            or not 0 <= priority <= 999
            or priority in priorities
            or not (device.get("tracker") or device.get("room"))
        ):
            raise ValueError("invalid_device")
        charging_age = device.get("charging_age")
        if charging_age is not None and (
            isinstance(charging_age, bool)
            or not isinstance(charging_age, (int, float))
            or not 1 <= charging_age <= 86400
        ):
            raise ValueError("invalid_device")
        keys.add(key)
        names.add(name.casefold())
        priorities.add(priority)
        for field in SOURCE_FIELDS:
            entity = device.get(field)
            if not entity:
                continue
            domains = (
                ("device_tracker",)
                if field in ("tracker", "local_tracker")
                else ("sensor", "binary_sensor", "input_boolean")
            )
            if not isinstance(entity, str) or not re.fullmatch(
                r"(?:" + "|".join(domains) + r")\.[a-z0-9_]+", entity
            ):
                raise ValueError("invalid_device")
            if field in ("tracker", "room"):
                if entity in trackers:
                    raise ValueError("duplicate_source")
                trackers.add(entity)
    return result


def timestamp(value, timezone):
    """Parse full timestamps only; HH:MM alone is ambiguous across midnight."""
    try:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value) if isfinite(value) else None
        if isinstance(value, str):
            if value.replace(".", "", 1).isdigit():
                return timestamp(float(value), timezone)
            if not re.match(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}", value):
                return None
            value = datetime.fromisoformat(value)
        if isinstance(value, datetime):
            if value.tzinfo:
                return value.timestamp()
            zone = ZoneInfo(timezone)
            variants = [value.replace(tzinfo=zone, fold=fold) for fold in (0, 1)]
            valid = {
                v.timestamp()
                for v in variants
                if v.astimezone(UTC).astimezone(zone).replace(tzinfo=None) == value
            }
            return next(iter(valid)) if len(valid) == 1 else None
    except ValueError, TypeError, OverflowError:
        pass
    return None


class StateLike(Protocol):
    state: str
    attributes: Mapping[str, Any]
    last_reported: datetime


def available(state: StateLike | None) -> TypeGuard[StateLike]:
    return (
        state is not None
        and state.state.lower() not in ("unknown", "unavailable", "")
        and not state.attributes.get("restored")
    )


def observed_at(state, timezone):
    if not available(state):
        return None
    for key in ("last_contact", "last_seen", "last_located", "located"):
        if key in state.attributes:
            return timestamp(state.attributes[key], timezone)
    return timestamp(state.last_reported, timezone)


def is_string_room_source(entity_id, state):
    if (
        state is None
        or not entity_id.startswith("sensor.")
        or state.attributes.get("unit_of_measurement") is not None
    ):
        return False
    if state.attributes.get("device_class") not in (
        None,
        "enum",
        "bermuda__custom_device_class",
    ):
        return False
    if state.state.lower() in ("on", "off", "true", "false"):
        return False
    try:
        float(state.state)
    except ValueError, TypeError:
        return True
    return False


def is_position_source(state):
    return (
        state is not None
        and state.attributes.get("source_type")
        not in ("router", "bluetooth", "bluetooth_le")
        and state.attributes.get("tracking_type") != "connection"
    )


def is_worn_source(entity_id, state, *, manual=False):
    if state is None or entity_id.split(".", 1)[0] not in (
        "sensor",
        "binary_sensor",
        "input_boolean",
    ):
        return False
    if state.attributes.get("device_class") not in (
        None,
        "enum",
        "presence",
        "occupancy",
    ):
        return False
    return manual or bool(
        re.search(
            r"(?:^|_)(?:worn|wearing|on_body|on_wrist)(?:_|$)",
            entity_id.split(".", 1)[1],
        )
    )


def charging_age_limit(config, signal_age, catalog=None):
    """Charging has its own bounded age; wearing/location windows stay independent."""
    if config.get("charging_age") is not None:
        return config["charging_age"]
    snapshot = catalog.snapshots.get(config.get("charging")) if catalog else None
    if snapshot and snapshot.platform == "icloud3":
        return max(signal_age, 1800 if config.get("wearable") else 9000)
    return signal_age


def observe(
    config,
    get_state,
    now,
    timezone,
    signal_age,
    max_accuracy,
    *,
    catalog=None,
    places=None,
):
    notes = []
    codes = []
    quality = "measurement"
    excluded, worn = None, None
    charge = get_state(config.get("charging")) if config.get("charging") else None
    charge_required = bool(
        config.get("wearable") or config.get("exclude_charging", False)
    )
    if config.get("charging"):
        value = (
            charge.state.lower().replace(" ", "").replace("_", "")
            if available(charge)
            else ""
        )
        charge_fresh = available(charge) and fresh(
            observed_at(charge, timezone),
            now,
            charging_age_limit(config, signal_age, catalog),
        )
        if (
            charge_fresh
            and value
            in (
                "charging",
                "charged",
                "full",
                "on",
                "true",
                "notcharging",
                "discharging",
                "off",
                "false",
            )
            and not fresh(observed_at(charge, timezone), now, signal_age)
        ):
            codes.append("charging_status_grace")
        if charge_fresh and value in ("charging", "charged", "full", "on", "true"):
            if charge_required:
                excluded = "charging"
        elif not charge_fresh or value not in (
            "notcharging",
            "discharging",
            "off",
            "false",
        ):
            notes.append("Charging status unavailable or stale")
            if charge_required:
                excluded = "charging status unconfirmed"
    wear = get_state(config.get("worn")) if config.get("worn") else None
    if (
        available(wear)
        and is_worn_source(config["worn"], wear, manual=True)
        and fresh(observed_at(wear, timezone), now, signal_age)
    ):
        if wear.state.lower() in ("on", "true", "worn"):
            worn = True
        elif wear.state.lower() in ("off", "false", "not_worn"):
            worn = False
            excluded = "not worn"
    if worn is None and config.get("wearable"):
        notes.append("Wearing status unconfirmed")
    if config.get("worn") and worn is None:
        excluded = "wearing status unconfirmed"
    location, located, latitude, longitude, accuracy = None, None, None, None, None
    tracker = get_state(config.get("tracker")) if config.get("tracker") else None
    if available(tracker) and is_position_source(tracker):
        attrs = tracker.attributes
        raw_time = None
        if config.get("timestamp_entity"):
            ts = get_state(config["timestamp_entity"])
            if available(ts):
                raw_time = (
                    ts.attributes.get(config["timestamp_attribute"])
                    if config.get("timestamp_attribute")
                    else ts.state
                )
        elif config.get("timestamp_attribute"):
            raw_time = attrs.get(config["timestamp_attribute"])
        else:
            raw_time = attrs.get(
                "located", attrs.get("last_located", attrs.get("last_timestamp"))
            )
            if (
                raw_time is None
                and str(attrs.get("integration", "")).lower() != "icloud3"
                and not (
                    catalog
                    and config.get("tracker") in catalog.snapshots
                    and catalog.snapshots[config["tracker"]].platform == "icloud3"
                )
            ):
                raw_time = tracker.last_reported
                quality = "report"
        located = timestamp(raw_time, timezone)
        try:
            latitude, longitude = float(attrs["latitude"]), float(attrs["longitude"])
            accuracy = float(
                attrs.get("gps_accuracy", 0 if catalog is None else float("nan"))
            )
            if (
                located is None
                or not all(isfinite(v) for v in (latitude, longitude, accuracy))
                or not -90 <= latitude <= 90
                or not -180 <= longitude <= 180
                or not 0 <= accuracy <= max_accuracy
            ):
                raise ValueError
            location = tracker.state
        except KeyError, ValueError, TypeError:
            location, located, latitude, longitude, accuracy = (
                None,
                None,
                None,
                None,
                None,
            )
            notes.append("No valid geographical fix and observation timestamp")
            codes.append(
                "timestamp_invalid"
                if timestamp(raw_time, timezone) is None
                else "poor_accuracy"
            )
    if config.get("tracker") and tracker is None:
        codes.append("missing_source")
    elif config.get("tracker") and not available(tracker):
        codes.append("source_unavailable")
    if available(tracker) and not is_position_source(tracker):
        codes.append("unsupported_tracker_source")
    room, room_at = None, None
    area = get_state(config.get("room")) if config.get("room") else None
    local = (
        get_state(config.get("local_tracker")) if config.get("local_tracker") else None
    )
    guard_required = bool(config.get("local_tracker"))
    area_snapshot = catalog.snapshots.get(config.get("room")) if catalog else None
    report_only = available(area) and not any(
        k in area.attributes
        for k in ("last_contact", "last_seen", "last_located", "located")
    )
    if (
        area_snapshot
        and area_snapshot.platform == "bermuda"
        and report_only
        and not guard_required
    ):
        guard_required = True
        guards = [
            candidate
            for candidate in catalog.candidates("local_tracker")
            if area_snapshot.device_id
            and catalog.snapshots[candidate.entity_id].device_id
            == area_snapshot.device_id
        ]
        fresh_guards = [
            candidate
            for g in guards
            if available(candidate := get_state(g.entity_id))
            and candidate.state in ("home", "not_home")
            and fresh(observed_at(candidate, timezone), now, signal_age)
        ]
        local = max(
            fresh_guards,
            key=lambda candidate: (
                observed_at(candidate, timezone),
                candidate.state != "home",
            ),
            default=None,
        )
    if (
        available(area)
        and area.state.lower() not in INVALID
        and is_string_room_source(config["room"], area)
    ):
        if not guard_required or (
            available(local)
            and local.state == "home"
            and fresh(observed_at(local, timezone), now, signal_age)
        ):
            room, room_at = area.state, observed_at(area, timezone)
            if not any(
                k in area.attributes
                for k in ("last_contact", "last_seen", "last_located", "located")
            ):
                quality = "report"
        else:
            notes.append("Local tracker does not confirm home")
            codes.append("local_guard_away")
    if available(area) and not is_string_room_source(config["room"], area):
        codes.append("unsupported_room_source")
    if config.get("room") and not available(area):
        codes.append("missing_source" if area is None else "no_room")
    area_id = area.attributes.get("area_id") if available(area) and room else None
    zone_id = None
    if places is not None:
        if area_id not in places.areas:
            area_id = None
        if area_id:
            room = places.area_name(area_id)
        if location is not None and tracker is not None:
            reported = tracker.attributes.get("in_zones", [])
            zone_id = places.resolve_zone(
                latitude, longitude, reported if isinstance(reported, list) else []
            )
            location = (
                "home" if zone_id == "zone.home" else zone_id if zone_id else "not_home"
            )
    return Observation(
        key=config["key"],
        priority=config["priority"],
        worn=worn,
        excluded=excluded,
        location=location,
        location_at=located,
        room=room,
        room_at=room_at,
        latitude=latitude,
        longitude=longitude,
        accuracy=accuracy,
        notes=tuple(notes),
        area_id=area_id,
        zone_id=zone_id,
        gps_source_entity_id=config.get("tracker"),
        room_source_entity_id=config.get("room"),
        timestamp_quality=quality,
        reason_codes=tuple(codes),
    )
