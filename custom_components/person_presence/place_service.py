"""Shared HA lifecycle for optional authorized geocoding."""

from homeassistant.core import SupportsResponse, callback
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .geocoding import PlaceLookup
from .lookup_settings import async_snapshot, effective_options
from .providers import async_request

KEY = DOMAIN + "_places"


def sync_lookup(hass, lookup, excluding=None):
    options = effective_options(hass, excluding)
    previous = lookup.generation
    lookup.configure(options)
    if previous != lookup.generation:
        for entry in hass.config_entries.async_entries(DOMAIN):
            if entry.entry_id in lookup.users:
                entry.runtime_data.invalidate_place()
                entry.runtime_data.async_update_listeners()


async def get_lookup(hass):
    import asyncio

    lock = hass.data.setdefault(KEY + "_init_lock", asyncio.Lock())
    async with lock:
        return await _get_lookup(hass)


async def _get_lookup(hass):
    if KEY in hass.data:
        return hass.data[KEY]
    store: Store[dict] = Store(
        hass, 1, DOMAIN + ".place_cache", private=True, atomic_writes=True
    )

    async def request(url, params):
        return await async_request(hass, dict(hass.data[KEY].options), params)

    lookup = PlaceLookup(request)
    lookup.users = set()
    hass.data[KEY] = lookup
    settings = await async_snapshot(hass)
    lookup.configure(settings["options"])
    try:
        saved = await store.async_load()
    except OSError, ValueError:
        saved = {}
    lookup.restore(saved or {})

    @callback
    def schedule_expiry():
        if lookup.expiry_handle:
            lookup.expiry_handle.cancel()
            lookup.expiry_handle = None
        if lookup.cache:
            delay = max(
                0.01,
                min(item["at"] + 30 * 86400 for item in lookup.cache.values())
                - lookup.clock()
                + 0.01,
            )
            lookup.expiry_handle = hass.loop.call_later(delay, lookup.prune)

    @callback
    def changed():
        store.async_delay_save(lambda: lookup.cache, 0)
        schedule_expiry()

    lookup.on_change = changed
    # Persist startup filtering even if there will never be another request.
    if saved is not None:
        await store.async_save(lookup.cache)
    schedule_expiry()

    @callback
    def stop_timer(event):
        if lookup.expiry_handle:
            lookup.expiry_handle.cancel()
            lookup.expiry_handle = None

    hass.bus.async_listen_once("homeassistant_stop", stop_timer)

    async def clear(call):
        if call.context.user_id:
            user = await hass.auth.async_get_user(call.context.user_id)
            if user is None or not user.is_admin:
                raise Unauthorized()
        lookup.clear()
        await store.async_save({})
        for entry in hass.config_entries.async_entries(DOMAIN):
            if entry.entry_id in lookup.users:
                entry.runtime_data.invalidate_place()
                entry.runtime_data.async_update_listeners()

    hass.services.async_register(
        DOMAIN, "clear_place_cache", clear, supports_response=SupportsResponse.NONE
    )
    return lookup


def fix_key(runtime, now):
    result = runtime.data
    if (
        runtime._stopped
        or not runtime.config.get("geocode", False)
        or result.pending
        or result.context != "away"
        or runtime.travel.result.distance_m is None
        or result.gps_observed_at is None
        or now - result.gps_observed_at > runtime.config["gps_age"]
    ):
        return None
    return (
        result.selected,
        result.gps_source_entity_id,
        result.gps_observed_at,
        result.latitude,
        result.longitude,
    )


def update_place(runtime, result, now):
    # Resolver data is available before state publication; no I/O on inference path.
    runtime.data = result
    key = fix_key(runtime, now)
    if key == runtime.place_key:
        if (
            key is None
            or runtime.place_label is not None
            or runtime.place_task is not None
            and not runtime.place_task.done()
            or now < max(runtime.place_retry_at, runtime.lookup.retry_at)
        ):
            return
    runtime.invalidate_place()
    runtime.place_key = key
    if key is None or not runtime.lookup.options:
        return
    generation = runtime.lookup.generation

    async def resolve():
        label = await runtime.lookup.resolve(key[3], key[4])
        from homeassistant.util import dt as dt_util

        if (
            not runtime._stopped
            and runtime.place_key == key
            and generation == runtime.lookup.generation
            and fix_key(runtime, dt_util.utcnow().timestamp()) == key
        ):
            runtime.place_label = label
            runtime.place_retry_at = (
                max(runtime.lookup.retry_at, runtime.lookup.clock() + 60)
                if label is None
                else 0.0
            )
            runtime.async_update_listeners()

    runtime.place_task = runtime.hass.async_create_task(resolve())
