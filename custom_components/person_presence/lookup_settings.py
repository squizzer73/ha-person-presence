"""Private installation-wide lookup settings, committed only by final flow Save."""

import asyncio
from copy import deepcopy

from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .providers import validate_provider_options

KEY = DOMAIN + "_lookup_settings"


def _legacy(hass, excluding=None):
    owners = [
        e
        for e in hass.config_entries.async_entries(DOMAIN)
        if e.entry_id != excluding and {**e.data, **e.options}.get("place_lookup")
    ]
    return (
        validate_provider_options(
            {**owners[0].data, **owners[0].options}["place_lookup"]
        )
        if owners
        else {}
    )


def effective_options(hass, excluding=None):
    handle = hass.data.get(KEY)
    record = handle.get("record") if handle else None
    return (
        deepcopy(record["options"]) if record is not None else _legacy(hass, excluding)
    )


async def _handle(hass):
    handle = hass.data.setdefault(
        KEY,
        {
            "lock": asyncio.Lock(),
            "loaded": False,
            "record": None,
            "store": Store(
                hass, 1, DOMAIN + ".lookup_settings", private=True, atomic_writes=True
            ),
        },
    )
    async with handle["lock"]:
        if not handle["loaded"]:
            try:
                record = await handle["store"].async_load()
                if record is not None:
                    if (
                        not isinstance(record, dict)
                        or not isinstance(record.get("revision"), int)
                        or not isinstance(record.get("options"), dict)
                    ):
                        raise ValueError("invalid_settings")
                    record = {
                        "revision": record["revision"],
                        "options": validate_provider_options(record["options"]),
                    }
            except ValueError, OSError:
                record = {"revision": 0, "options": {}}
            handle["record"] = record
            handle["loaded"] = True
    return handle


def _snapshot(hass, handle):
    return {
        "revision": handle["record"]["revision"] if handle["record"] else 0,
        "options": effective_options(hass),
    }


async def async_snapshot(hass):
    handle = await _handle(hass)
    async with handle["lock"]:
        return _snapshot(hass, handle)


async def async_save(hass, expected, options):
    options = validate_provider_options(options)
    handle = await _handle(hass)
    async with handle["lock"]:
        current = _snapshot(hass, handle)
        if expected != current:
            raise ValueError("lookup_changed")
        record = {"revision": current["revision"] + 1, "options": options}
        try:
            await handle["store"].async_save(record)
        except OSError:
            raise ValueError("cannot_save") from None
        handle["record"] = deepcopy(record)
        return deepcopy(record)


async def async_remove_settings(hass):
    handle = await _handle(hass)
    async with handle["lock"]:
        await handle["store"].async_remove()
        handle["record"] = None
