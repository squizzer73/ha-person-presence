"""Regressions from the independent 0.3.0b1 bug audit; fictional devices only."""

import asyncio
import time
import unittest
from types import SimpleNamespace

from test_engine import load
from test_inputs import state

engine = load("engine")
inputs = load("inputs")
sources = load("sources")


class RoomRegressions(unittest.TestCase):
    def test_older_away_fix_does_not_clear_newer_room_while_settling(self):
        resolver = engine.Resolver(settle=15)

        def obs(room, at, gps=990):
            return engine.Observation(
                key="phone",
                priority=1,
                location="not_home",
                location_at=gps,
                room=room,
                room_at=at,
            )

        resolver.update([obs("Kitchen", 999)], 1000)
        self.assertEqual(resolver.update([obs("Kitchen", 999)], 1015).room, "Kitchen")
        self.assertEqual(resolver.update([obs("Study", 1020)], 1020).room, "Kitchen")
        self.assertEqual(resolver.update([obs("Study", 1020)], 1035).room, "Study")
        self.assertIsNone(
            resolver.update([obs("Study", 1020, gps=1040)], 1040).location
        )

    def test_away_fix_between_accepted_and_latest_room_does_not_clear_hold(self):
        resolver = engine.Resolver(settle=15)

        def obs(room, at, gps=990):
            return engine.Observation(
                key="p",
                priority=1,
                location="not_home",
                location_at=gps,
                room=room,
                room_at=at,
            )

        resolver.update([obs("Kitchen", 999)], 1000)
        resolver.update([obs("Kitchen", 999)], 1015)
        self.assertEqual(
            resolver.update([obs("Study", 1020, gps=1010)], 1020).room, "Kitchen"
        )

    def observe(self, guards, *, explicit=None):
        states = {"sensor.device_area": state("Kitchen", at=999)} | guards
        rows = [
            sources.SourceSnapshot(
                id, s.state, s.attributes, s.last_reported, "bermuda", "same_device"
            )
            for id, s in states.items()
        ]
        config = {
            "key": "p",
            "name": "Phone",
            "priority": 1,
            "room": "sensor.device_area",
            "wearable": False,
        }
        if explicit:
            config["local_tracker"] = explicit
        return inputs.observe(
            config,
            states.get,
            1000,
            "UTC",
            600,
            100,
            catalog=sources.SourceCatalog(rows),
        )

    def test_auto_guard_uses_fresh_alternative(self):
        self.assertEqual(
            self.observe(
                {
                    "device_tracker.a_old": state(
                        "home", at=1, source_type="bluetooth_le"
                    ),
                    "device_tracker.b_new": state(
                        "home", at=999, source_type="bluetooth_le"
                    ),
                }
            ).room,
            "Kitchen",
        )

    def test_newer_or_equal_negative_guard_blocks_older_positive(self):
        for negative_at in [999, 1000]:
            self.assertIsNone(
                self.observe(
                    {
                        "device_tracker.a_home": state(
                            "home", at=999, source_type="bluetooth_le"
                        ),
                        "device_tracker.b_away": state(
                            "not_home", at=negative_at, source_type="bluetooth_le"
                        ),
                    }
                ).room
            )
        self.assertIsNone(
            self.observe(
                {"device_tracker.only": state("home", at=1, source_type="bluetooth_le")}
            ).room
        )

    def test_explicit_guard_is_not_replaced_by_auto_candidate(self):
        self.assertIsNone(
            self.observe(
                {
                    "device_tracker.a_old": state(
                        "home", at=1, source_type="bluetooth_le"
                    ),
                    "device_tracker.b_new": state(
                        "home", at=999, source_type="bluetooth_le"
                    ),
                },
                explicit="device_tracker.a_old",
            ).room
        )


class LookupRegressions(unittest.IsolatedAsyncioTestCase):
    async def test_endpoint_switch_resets_only_provider_backoff(self):
        geo = load("geocoding")
        now = [time.time()]
        calls = []

        async def request(url, params):
            calls.append(url)
            if len(calls) == 1:
                raise OSError("temporary outage")
            return {"display_name": "Square"}

        lookup = geo.PlaceLookup(request, spacing=0, clock=lambda: now[0])
        lookup.configure(
            {"endpoint": "https://old.example/reverse", "authorized": True}
        )
        await lookup.resolve(1, 2)
        failed_until = lookup.retry_at
        last = lookup.last_request
        lookup.clear()
        self.assertEqual(lookup.retry_at, failed_until)
        lookup.configure(
            {"endpoint": "https://new.example/reverse", "authorized": True}
        )
        self.assertEqual(lookup.last_request, last)
        self.assertEqual((await lookup.resolve(1, 2)).label, "Square")
        self.assertEqual(len(calls), 2)

    def runtime(self, lookup):
        runtime = SimpleNamespace(
            config={"geocode": True, "gps_age": 3600},
            lookup=lookup,
            travel=SimpleNamespace(result=SimpleNamespace(distance_m=100)),
            place_key=None,
            place_label=None,
            place_task=None,
            place_retry_at=0,
            _stopped=False,
            hass=SimpleNamespace(async_create_task=asyncio.create_task),
            async_update_listeners=lambda: None,
        )

        def invalidate():
            runtime.place_key = None
            runtime.place_label = None
            runtime.place_retry_at = 0
            if runtime.place_task and not runtime.place_task.done():
                runtime.place_task.cancel()
            runtime.place_task = None

        runtime.invalidate_place = invalidate
        return runtime

    async def test_same_fresh_fix_retries_after_backoff_without_busy_loop(self):
        geo = load("geocoding")
        service = load("place_service")
        now = [time.time()]
        calls = []

        async def request(url, params):
            calls.append(url)
            if len(calls) == 1:
                raise OSError("temporary outage")
            return {"display_name": "Recovered square"}

        lookup = geo.PlaceLookup(request, spacing=0, clock=lambda: now[0])
        lookup.configure(
            {"endpoint": "https://maps.example/reverse", "authorized": True}
        )
        runtime = self.runtime(lookup)
        result = engine.Result(
            location="not_home",
            selected="phone",
            context="away",
            latitude=1,
            longitude=2,
            gps_observed_at=now[0],
            gps_source_entity_id="device_tracker.phone",
        )
        service.update_place(runtime, result, now[0])
        await runtime.place_task
        for _ in range(3):
            service.update_place(runtime, result, now[0] + 5)
            await asyncio.sleep(0)
        self.assertEqual(len(calls), 1)
        now[0] += 601
        service.update_place(runtime, result, now[0])
        await runtime.place_task
        self.assertEqual(len(calls), 2)
        self.assertEqual(runtime.place_label.label, "Recovered square")
        service.update_place(runtime, result, now[0] + 5)
        await asyncio.sleep(0)
        self.assertEqual(len(calls), 2)

    async def test_failed_fix_does_not_retry_when_disabled_or_expired(self):
        geo = load("geocoding")
        service = load("place_service")
        now = [time.time()]
        calls = []

        async def request(url, params):
            calls.append(url)
            raise OSError("outage")

        lookup = geo.PlaceLookup(request, spacing=0, clock=lambda: now[0])
        lookup.configure(
            {"endpoint": "https://maps.example/reverse", "authorized": True}
        )
        runtime = self.runtime(lookup)
        result = engine.Result(
            location="not_home",
            selected="p",
            context="away",
            latitude=1,
            longitude=2,
            gps_observed_at=now[0],
        )
        service.update_place(runtime, result, now[0])
        await runtime.place_task
        runtime.config["geocode"] = False
        now[0] += 601
        service.update_place(runtime, result, now[0])
        await asyncio.sleep(0)
        self.assertEqual(len(calls), 1)
        runtime.config["geocode"] = True
        now[0] += 3601
        service.update_place(runtime, result, now[0])
        await asyncio.sleep(0)
        self.assertEqual(len(calls), 1)

    async def test_empty_response_uses_minimum_retry_delay(self):
        geo = load("geocoding")
        service = load("place_service")
        now = [time.time()]
        calls = []

        async def request(url, params):
            calls.append(url)
            return {} if len(calls) == 1 else {"display_name": "Square"}

        lookup = geo.PlaceLookup(request, spacing=0, clock=lambda: now[0])
        lookup.configure(
            {"endpoint": "https://maps.example/reverse", "authorized": True}
        )
        runtime = self.runtime(lookup)
        result = engine.Result(
            location="not_home",
            selected="p",
            context="away",
            latitude=1,
            longitude=2,
            gps_observed_at=now[0],
        )
        service.update_place(runtime, result, now[0])
        await runtime.place_task
        now[0] += 59
        service.update_place(runtime, result, now[0])
        await asyncio.sleep(0)
        self.assertEqual(len(calls), 1)
        now[0] += 2
        service.update_place(runtime, result, now[0])
        await runtime.place_task
        self.assertEqual(runtime.place_label.label, "Square")
        self.assertEqual(len(calls), 2)

    async def test_same_key_does_not_duplicate_inflight_request(self):
        geo = load("geocoding")
        service = load("place_service")
        now = time.time()
        gate = asyncio.Event()
        calls = []

        async def request(url, params):
            calls.append(url)
            await gate.wait()
            return {"display_name": "Square"}

        lookup = geo.PlaceLookup(request, spacing=0)
        lookup.configure(
            {"endpoint": "https://maps.example/reverse", "authorized": True}
        )
        runtime = self.runtime(lookup)
        result = engine.Result(
            location="not_home",
            selected="p",
            context="away",
            latitude=1,
            longitude=2,
            gps_observed_at=now,
        )
        service.update_place(runtime, result, now)
        first = runtime.place_task
        await asyncio.sleep(0)
        for _ in range(3):
            service.update_place(runtime, result, now + 5)
            await asyncio.sleep(0)
        self.assertIs(runtime.place_task, first)
        self.assertEqual(len(calls), 1)
        gate.set()
        await first
        self.assertEqual(runtime.place_label.label, "Square")

    async def test_stopped_runtime_never_retries(self):
        geo = load("geocoding")
        service = load("place_service")
        now = [time.time()]
        calls = []

        async def request(url, params):
            calls.append(url)
            raise OSError("outage")

        lookup = geo.PlaceLookup(request, spacing=0, clock=lambda: now[0])
        lookup.configure(
            {"endpoint": "https://maps.example/reverse", "authorized": True}
        )
        runtime = self.runtime(lookup)
        result = engine.Result(
            location="not_home",
            selected="p",
            context="away",
            latitude=1,
            longitude=2,
            gps_observed_at=now[0],
        )
        service.update_place(runtime, result, now[0])
        await runtime.place_task
        runtime._stopped = True
        runtime.invalidate_place()
        now[0] += 601
        service.update_place(runtime, result, now[0])
        await asyncio.sleep(0)
        self.assertEqual(len(calls), 1)
        self.assertIsNone(runtime.place_task)
