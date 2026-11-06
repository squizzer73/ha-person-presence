"""Readable health explanations without inventing probability or physical certainty."""

from dataclasses import dataclass

DESCRIPTIONS = {
    "unsupported_room_source": "Room source is not a supported string area sensor",
    "unsupported_tracker_source": "Tracker reports a connection rather than geographical position",
    "unsupported_worn_source": "Source does not report wearing status",
    "selected": "Selected source",
    "lower_preference": "A preferred eligible device is selected",
    "charging": "Device is charging",
    "not_worn": "Device reports that it is not worn",
    "eligibility_unconfirmed": "Charging or wearing status is unconfirmed",
    "missing_source": "A configured source is missing",
    "source_unavailable": "Source is unavailable",
    "stale_location": "GPS observation is too old",
    "poor_accuracy": "GPS coordinates or accuracy are unsuitable",
    "no_room": "No current room reading",
    "local_guard_away": "Local tracker does not confirm home",
    "timestamp_invalid": "Observation timestamp is missing or invalid",
    "timestamp_quality_limited": "Provider contact/report time is used; measurement time is unconfirmed",
    "conflicting_evidence": "Room and geographical evidence conflict",
    "settling": "Waiting for the change to settle",
    "no_fresh_evidence": "No fresh location evidence",
}


@dataclass(frozen=True)
class SourceHealth:
    evidence: dict

    @classmethod
    def from_evidence(cls, evidence):
        return cls(dict(evidence))

    def explanations(self, key, now):
        item = self.evidence.get(key, {})
        parts = [
            DESCRIPTIONS.get(code, "Source needs review")
            for code in item.get("reasons", [])
        ]
        at = item.get("gps_observed_at")
        if at is not None:
            age = max(0, now - at)
            parts.append(f"Last GPS observation: {int(age // 60)} minutes ago")
        room_at = item.get("room_observed_at")
        if room_at is not None:
            age = max(0, now - room_at)
            parts.append(f"Last room observation/report: {int(age)} seconds ago")
        for field, label in (
            ("gps_source_entity_id", "GPS source"),
            ("room_source_entity_id", "Room source"),
        ):
            if item.get(field):
                parts.append(label + ": " + item[field])
        return parts or ["No source report"]

    def describe(self, key, now):
        return "; ".join(self.explanations(key, now))
