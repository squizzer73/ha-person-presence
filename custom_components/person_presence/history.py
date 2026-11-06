"""Validate retained display history without asserting a current location."""

from math import isfinite


def restore_record(data, person, sources, now):
    if not isinstance(data, dict):
        return None
    value, observed = data.get("value"), data.get("observed_at")
    if (
        not isinstance(value, str)
        or not 0 < len(value) <= 255
        or isinstance(observed, bool)
        or not isinstance(observed, (int, float))
        or not 0 <= observed <= now
        or not isfinite(observed)
        or data.get("person_entity_id") != person
        or not isinstance(data.get("source_entity_id"), str)
        or data.get("source_entity_id") not in sources
    ):
        return None
    return {
        key: data[key]
        for key in ("value", "observed_at", "person_entity_id", "source_entity_id")
    }
