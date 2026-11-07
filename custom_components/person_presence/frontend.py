"""Serve the bundled local card without changing dashboard layouts."""

import asyncio
import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.lovelace.resources import ResourceStorageCollection

CARD_PATH = "/person_presence/person-presence-card.js"
CARD_URL = CARD_PATH + "?v=0.4.0b1"
_LOGGER = logging.getLogger(__name__)


async def ensure_resource(resources):
    await resources.async_get_info()
    existing = [
        r
        for r in resources.async_items()
        if r.get("url", "").split("?")[0] == CARD_PATH
    ]
    if existing:
        if existing[0]["url"] != CARD_URL:
            await resources.async_update_item(
                existing[0]["id"], {"url": CARD_URL, "res_type": "module"}
            )
    else:
        await resources.async_create_item({"url": CARD_URL, "res_type": "module"})


async def setup_frontend(hass):
    lock = hass.data.setdefault("person_presence_frontend_lock", asyncio.Lock())
    async with lock:
        await _setup_frontend(hass)


async def _setup_frontend(hass):
    if hass.data.get("person_presence_frontend"):
        return
    if not getattr(hass, "http", None):
        return
    if not hass.data.get("person_presence_static_path"):
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    CARD_PATH,
                    str(Path(__file__).parent / "www/person-presence-card.js"),
                    False,
                )
            ]
        )
        hass.data["person_presence_static_path"] = True
    data = hass.data.get(LOVELACE_DATA)
    if data and isinstance(data.resources, ResourceStorageCollection):
        await ensure_resource(data.resources)
    else:
        _LOGGER.info(
            "Add dashboard module resource %s to use the bundled Person Presence card",
            CARD_URL,
        )
    hass.data["person_presence_frontend"] = True
