"""Shared virtual device identity for a person's presence outputs."""

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .const import DOMAIN


def presence_device_info(entry):
    """Use the stable config-entry identity; labels remain user-configurable."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.runtime_data.config["name"],
        manufacturer="Person Presence",
        model="Person presence",
        entry_type=DeviceEntryType.SERVICE,
    )
