"""Unsaved inference preview, isolated from live resolver and persistence."""

from dataclasses import dataclass

from .engine import Resolver
from .health import SourceHealth
from .inputs import observe, validate_config
from .whereabouts import project_whereabouts


@dataclass(frozen=True)
class PreviewResult:
    value: str | None
    selected_device: str | None
    evidence: dict
    summary: str
    missing_capabilities: dict


def build_preview(config, catalog, places, now):
    config = validate_config(config)
    observations = [
        observe(
            d,
            catalog.get_state,
            now,
            config.get("timezone", "UTC"),
            config["signal_age"],
            config["max_accuracy"],
            catalog=catalog,
            places=places,
        )
        for d in config["devices"]
    ]
    result = Resolver(
        settle=0, gps_age=config["gps_age"], room_age=config["room_age"]
    ).update(observations, now)
    names = {d["key"]: d["name"] for d in config["devices"]}
    output = project_whereabouts(result, places, config["person"], names)
    health = SourceHealth.from_evidence(result.evidence)
    missing = {
        d["key"]: [role for role in ("tracker", "room", "worn") if not d.get(role)]
        for d in config["devices"]
    }
    labels = {
        "tracker": "Outdoor location",
        "room": "Room",
        "worn": "Wearing status (optional)",
    }
    blocks = ["**Proposed whereabouts:** " + (output.value or "Unknown")]
    for key in result.evidence:
        lines = health.explanations(key, now)
        lines += [labels[role] + ": not configured" for role in missing[key]]
        blocks.append(
            "**" + names[key] + "**\n\n" + "\n".join("- " + line for line in lines)
        )
    summary = "\n\n".join(blocks)
    return PreviewResult(
        output.value, names.get(result.selected), result.evidence, summary, missing
    )
