"""Actionable source repairs; normal away and stale GPS are not repair issues."""

from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN
from .inputs import SOURCE_FIELDS


def sync_missing_sources(hass, entry, config):
    missing = sorted(
        {
            d[field]
            for d in config["devices"]
            for field in SOURCE_FIELDS
            if d.get(field) and hass.states.get(d[field]) is None
        }
    )
    issue_id = entry.entry_id + "_missing_sources"
    if missing:
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="missing_sources",
            translation_placeholders={"sources": ", ".join(missing)},
            config_entry_id=entry.entry_id,
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, issue_id)


def remove_issues(hass, entry):
    ir.async_delete_issue(hass, DOMAIN, entry.entry_id + "_missing_sources")
