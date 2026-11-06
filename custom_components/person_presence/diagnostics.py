"""Allowlisted anonymous support data; raw provider payloads are never exported."""

from math import isfinite

from .health import DESCRIPTIONS
from .inputs import SOURCE_FIELDS


def redact_diagnostics(config, evidence):
    aliases: dict[str, str] = {}
    devices = []
    for index, device in enumerate(config.get("devices", []), 1):
        roles = {}
        for role in SOURCE_FIELDS:
            entity = device.get(role)
            if entity:
                roles[role] = aliases.setdefault(
                    entity, "entity_" + str(len(aliases) + 1)
                )
        item = evidence.get(device.get("key"), {})
        health = {"reasons": [r for r in item.get("reasons", []) if r in DESCRIPTIONS]}
        for key in ("gps_fresh", "room_fresh", "worn"):
            if isinstance(item.get(key), bool) or item.get(key) is None:
                health[key] = item.get(key)
        if item.get("timestamp_quality") in ("measurement", "report"):
            health["timestamp_quality"] = item["timestamp_quality"]
        kind = device.get("device_type", "other")
        devices.append(
            {
                "alias": f"device_{index}",
                "type": kind
                if kind in ("phone", "watch", "tablet", "tag", "other")
                else "other",
                "sources": roles,
                "health": health,
            }
        )
    settings = {
        k: v
        for k, v in config.items()
        if k in ("gps_age", "room_age", "signal_age", "settle", "max_accuracy")
        and isinstance(v, (int, float))
        and not isinstance(v, bool)
        and isfinite(v)
    }
    return {
        "format_version": 1,
        "settings": settings,
        "devices": devices,
        "privacy": "Identifiers, place names, coordinates, accounts and raw payloads omitted",
    }


async def async_get_config_entry_diagnostics(hass, entry):
    runtime = entry.runtime_data
    return redact_diagnostics(runtime.config, runtime.data.evidence)
