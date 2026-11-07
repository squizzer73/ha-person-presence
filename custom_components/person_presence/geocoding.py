"""Opt-in shared reverse lookup; no default endpoint or tracking decisions."""

import asyncio
import json
import time
from dataclasses import dataclass
from math import isfinite


async def read_json(content):
    payload = bytearray()
    async for chunk in content.iter_chunked(8192):
        payload.extend(chunk)
        if len(payload) > 65536:
            raise ValueError("Response too large")
    return json.loads(payload)


@dataclass(frozen=True)
class PlaceLabel:
    label: str
    attribution: str = ""
    provider: str = "custom"


def validate_options(options):
    from .providers import validate_provider_options

    return validate_provider_options(options)


class PlaceLookup:
    """Serial bounded requests, private bounded cache and generation invalidation."""

    def __init__(self, request, *, spacing=2, clock=time.time):
        self.expiry_handle: asyncio.TimerHandle | None = None
        self.users: set[str] = set()
        self.request = request
        self.spacing = spacing
        self.clock = clock
        self.options = {}
        self.cache = {}
        self.generation = 0
        self.lock = asyncio.Lock()
        self.last_request = 0.0
        self.retry_at = 0.0
        self.on_change = lambda: None

    def configure(self, options):
        options = validate_options(options)
        if options != self.options:
            if options.get("endpoint") != self.options.get("endpoint") or options.get(
                "api_key"
            ) != self.options.get("api_key"):
                self.retry_at = 0.0
            self.options = options
            self.clear()

    def clear(self):
        self.generation += 1
        self.cache.clear()
        self.on_change()

    def restore(self, cache):
        if not isinstance(cache, dict):
            return
        now = self.clock()
        for key, item in list(cache.items())[-1000:]:
            if (
                isinstance(key, str)
                and key.startswith(self.options.get("endpoint", "\0") + "|")
                and isinstance(item, dict)
                and isinstance(item.get("at"), (int, float))
                and 0 <= now - item["at"] < 30 * 86400
                and isinstance(item.get("label"), str)
                and 0 < len(item["label"]) <= 255
                and isinstance(item.get("attribution", ""), str)
            ):
                self.cache[key] = item

    def prune(self):
        now = self.clock()
        valid = {k: v for k, v in self.cache.items() if 0 <= now - v["at"] < 30 * 86400}
        if valid != self.cache:
            self.cache = valid
            self.on_change()

    async def resolve(self, latitude, longitude):
        if (
            not self.options
            or not isfinite(latitude)
            or not isfinite(longitude)
            or not -90 <= latitude <= 90
            or not -180 <= longitude <= 180
        ):
            return None
        generation = self.generation
        endpoint = self.options["endpoint"]
        key = f"{endpoint}|{latitude:.4f},{longitude:.4f}"
        async with self.lock:
            if generation != self.generation:
                return None
            now = self.clock()
            self.prune()
            if key in self.cache:
                item = self.cache[key]
                return PlaceLabel(
                    item["label"],
                    item.get("attribution", ""),
                    self.options.get("provider", "custom"),
                )
            if now < self.retry_at:
                return None
            await asyncio.sleep(max(0, self.spacing - (now - self.last_request)))
            if generation != self.generation:
                return None
            self.last_request = self.clock()
            try:
                async with asyncio.timeout(12):
                    data = await self.request(
                        endpoint,
                        {
                            "format": "jsonv2",
                            "lat": f"{latitude:.4f}",
                            "lon": f"{longitude:.4f}",
                        },
                    )
                label = data.get("display_name") if isinstance(data, dict) else None
                attribution = data.get("licence", "") if isinstance(data, dict) else ""
                if (
                    not isinstance(label, str)
                    or not label.strip()
                    or not isinstance(attribution, str)
                ):
                    return None
                if generation != self.generation:
                    return None
                item = {
                    "label": label.strip()[:255],
                    "attribution": attribution[:1000],
                    "at": self.clock(),
                }
                self.cache[key] = item
                while len(self.cache) > 1000:
                    del self.cache[next(iter(self.cache))]
                self.on_change()
                return PlaceLabel(
                    item["label"],
                    item["attribution"],
                    self.options.get("provider", "custom"),
                )
            except TimeoutError, OSError, ValueError:
                self.retry_at = self.clock() + 600
                return None
